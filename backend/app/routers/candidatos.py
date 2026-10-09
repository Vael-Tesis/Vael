"""Endpoints de gestión de candidatos y ranking — /api/candidatos/."""
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_rol
from app.core.security import emitir_token_candidato
from app.models.base import new_id, utcnow
from app.models.candidato import Candidato, ClasificacionIA, EstadoCandidato, NotaCandidato
from app.models.entrevista import EntrevistaIA
from app.models.evaluacion import Examen
from app.models.usuario import RolUsuario, TipoToken, Usuario
from app.models.vacante import Vacante
from app.schemas.candidato import (
    CambiarEstadoRequest,
    CandidatoResponse,
    CandidatoUpdateRequest,
    CargaMasivaResponse,
    MensajeResponse,
    NotaCreateRequest,
    NotaResponse,
    RankingCandidatoResponse,
)
from app.services.analisis_cv import analizar_cv_candidato
from app.services.aws_services import subir_archivo
from app.services.correos import correo_bienvenida_examen, correo_finalista, correo_invitacion_entrevista

router = APIRouter(prefix="/api/candidatos", tags=["candidatos"])

_RECLUTADOR_O_SUPERIOR = (RolUsuario.ADMIN, RolUsuario.GERENTE, RolUsuario.RECLUTADOR)
_ESTADOS_BANCO_TALENTO = (EstadoCandidato.CV_RECHAZADO, EstadoCandidato.EXAMEN_RECHAZADO, EstadoCandidato.DESCARTADO)
_CLASIFICACIONES_BUEN_SCORE = (ClasificacionIA.ALTAMENTE_RECOMENDADO, ClasificacionIA.RECOMENDADO)


async def _obtener_candidato_del_tenant(candidato_id: str, tenant_id: str, db: AsyncSession) -> Candidato:
    """Busca un candidato por id dentro del tenant actual, o lanza 404 si no existe."""
    statement = select(Candidato).where(Candidato.id == candidato_id, Candidato.tenant_id == tenant_id)
    result = await db.exec(statement)
    candidato = result.first()

    if candidato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidato no encontrado")

    return candidato


@router.get("", response_model=list[CandidatoResponse])
async def listar_candidatos(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    vacante_id: str | None = None,
    estado: EstadoCandidato | None = None,
    clasificacion_ia: ClasificacionIA | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Candidato]:
    """Lista los candidatos del tenant, con filtros opcionales por vacante, estado y clasificación IA."""
    statement = select(Candidato).where(Candidato.tenant_id == actor.tenant_id)

    if vacante_id is not None:
        statement = statement.where(Candidato.vacante_id == vacante_id)
    if estado is not None:
        statement = statement.where(Candidato.estado == estado)
    if clasificacion_ia is not None:
        statement = statement.where(Candidato.clasificacion_ia == clasificacion_ia)

    statement = statement.offset(skip).limit(limit)

    result = await db.exec(statement)
    return list(result.all())


@router.post("/", response_model=CandidatoResponse, status_code=status.HTTP_201_CREATED)
async def crear_candidato(
    background_tasks: BackgroundTasks,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    vacante_id: Annotated[str, Form()],
    nombre: Annotated[str, Form()],
    apellidos: Annotated[str, Form()],
    email: Annotated[EmailStr, Form()],
    cv: Annotated[UploadFile, File()],
    telefono: Annotated[str | None, Form()] = None,
    linkedin: Annotated[str | None, Form()] = None,
    github: Annotated[str | None, Form()] = None,
    portfolio: Annotated[str | None, Form()] = None,
    pretension_salarial: Annotated[float | None, Form()] = None,
) -> Candidato:
    """Registra manualmente un candidato para una vacante, sube su CV a S3 y dispara el análisis IA."""
    vacante = await db.get(Vacante, vacante_id)
    if vacante is None or vacante.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")

    contenido = await cv.read()
    clave = f"cvs/{actor.tenant_id}/{vacante_id}/{new_id()}_{cv.filename}"
    cv_url = await subir_archivo(contenido, clave, cv.content_type or "application/pdf")

    candidato = Candidato(
        tenant_id=actor.tenant_id,
        vacante_id=vacante_id,
        nombre=nombre,
        apellidos=apellidos,
        email=email,
        telefono=telefono,
        linkedin=linkedin,
        github=github,
        portfolio=portfolio,
        cv_url=cv_url,
        pretension_salarial=pretension_salarial,
    )
    db.add(candidato)
    await db.commit()
    await db.refresh(candidato)

    background_tasks.add_task(analizar_cv_candidato, candidato.id)
    return candidato


@router.get("/ranking", response_model=list[RankingCandidatoResponse])
async def ranking_candidatos(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    vacante_id: str,
) -> list[RankingCandidatoResponse]:
    """Ranking de candidatos de una vacante, ordenado por score_final descendente.

    Incluye la nota de examen y de entrevista de cada candidato (si ya las rindió),
    para que RRHH vea el desglose de las tres componentes del score ponderado.
    """
    statement = (
        select(Candidato)
        .where(
            Candidato.tenant_id == actor.tenant_id,
            Candidato.vacante_id == vacante_id,
            Candidato.score_final.is_not(None),
        )
        .order_by(Candidato.score_final.desc())
    )
    result = await db.exec(statement)
    candidatos = list(result.all())

    candidato_ids = [c.id for c in candidatos]
    notas_examen: dict[str, float] = {}
    notas_entrevista: dict[str, float] = {}

    if candidato_ids:
        examenes_statement = select(Examen).where(Examen.candidato_id.in_(candidato_ids))
        examenes_result = await db.exec(examenes_statement)
        notas_examen = {e.candidato_id: e.nota for e in examenes_result.all() if e.nota is not None}

        entrevistas_statement = select(EntrevistaIA).where(EntrevistaIA.candidato_id.in_(candidato_ids))
        entrevistas_result = await db.exec(entrevistas_statement)
        notas_entrevista = {e.candidato_id: e.nota for e in entrevistas_result.all() if e.nota is not None}

    return [
        RankingCandidatoResponse(
            **CandidatoResponse.model_validate(c).model_dump(),
            nota_examen=notas_examen.get(c.id),
            nota_entrevista=notas_entrevista.get(c.id),
        )
        for c in candidatos
    ]


@router.get("/banco-talento", response_model=list[CandidatoResponse])
async def banco_talento(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Candidato]:
    """Candidatos con buena clasificación IA que no avanzaron en su proceso (banco de talento)."""
    statement = select(Candidato).where(
        Candidato.tenant_id == actor.tenant_id,
        Candidato.clasificacion_ia.in_(_CLASIFICACIONES_BUEN_SCORE),
        Candidato.estado.in_(_ESTADOS_BANCO_TALENTO),
    )
    result = await db.exec(statement)
    return list(result.all())


@router.post("/carga-masiva", response_model=CargaMasivaResponse, status_code=status.HTTP_202_ACCEPTED)
async def carga_masiva_candidatos(
    background_tasks: BackgroundTasks,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    vacante_id: Annotated[str, Form()],
    archivos: Annotated[list[UploadFile], File()],
) -> CargaMasivaResponse:
    """Sube múltiples CVs para una vacante: crea un candidato por archivo y dispara su análisis IA.

    Como el CV recién se analiza en background, nombre/apellidos/email todavía no se
    conocen al momento de la carga — quedan con un valor provisional hasta que el
    análisis (una vez implementado) los complete.
    """
    vacante = await db.get(Vacante, vacante_id)
    if vacante is None or vacante.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")

    candidato_ids: list[str] = []

    for archivo in archivos:
        contenido = await archivo.read()
        clave = f"cvs/{actor.tenant_id}/{vacante_id}/{new_id()}_{archivo.filename}"
        cv_url = await subir_archivo(contenido, clave, archivo.content_type or "application/pdf")

        nombre_provisional = Path(archivo.filename or "candidato").stem.replace("_", " ").replace("-", " ").title()

        candidato = Candidato(
            tenant_id=actor.tenant_id,
            vacante_id=vacante_id,
            nombre=nombre_provisional or "Pendiente",
            apellidos="Por identificar",
            email=f"cv-{new_id()[:8]}@pendiente.vael",
            cv_url=cv_url,
        )
        db.add(candidato)
        await db.commit()
        await db.refresh(candidato)

        candidato_ids.append(candidato.id)
        background_tasks.add_task(analizar_cv_candidato, candidato.id)

    return CargaMasivaResponse(creados=len(candidato_ids), candidato_ids=candidato_ids)


@router.get("/{candidato_id}", response_model=CandidatoResponse)
async def obtener_candidato(
    candidato_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Candidato:
    """Retorna el detalle completo de un candidato."""
    return await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)


@router.put("/{candidato_id}", response_model=CandidatoResponse)
async def editar_candidato(
    candidato_id: str,
    body: CandidatoUpdateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Candidato:
    """Edita los campos provistos de un candidato (actualización parcial)."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(candidato, campo, valor)

    candidato.updated_at = utcnow()
    db.add(candidato)
    await db.commit()
    await db.refresh(candidato)
    return candidato


@router.post("/{candidato_id}/analizar", response_model=MensajeResponse, status_code=status.HTTP_202_ACCEPTED)
async def analizar_candidato(
    candidato_id: str,
    background_tasks: BackgroundTasks,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Dispara el análisis IA del CV de un candidato en background y responde de inmediato."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)

    candidato.estado = EstadoCandidato.CV_ANALIZANDO
    candidato.updated_at = utcnow()
    db.add(candidato)
    await db.commit()

    background_tasks.add_task(analizar_cv_candidato, candidato.id)

    return MensajeResponse(detail="Análisis de CV en curso")


@router.post("/{candidato_id}/cambiar-estado", response_model=CandidatoResponse)
async def cambiar_estado_candidato(
    candidato_id: str,
    body: CambiarEstadoRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Candidato:
    """Cambia manualmente el estado de un candidato."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)
    candidato.estado = body.estado
    candidato.updated_at = utcnow()
    db.add(candidato)
    await db.commit()
    await db.refresh(candidato)
    return candidato


@router.post("/{candidato_id}/marcar-finalista", response_model=CandidatoResponse)
async def marcar_finalista(
    candidato_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Candidato:
    """Marca a un candidato como finalista."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)
    candidato.es_finalista = True
    candidato.estado = EstadoCandidato.FINALISTA
    candidato.updated_at = utcnow()
    db.add(candidato)
    await db.commit()
    await db.refresh(candidato)
    return candidato


@router.post("/{candidato_id}/reenviar-correo-etapa", response_model=MensajeResponse)
async def reenviar_correo_etapa(
    candidato_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Reenvía el correo correspondiente a la etapa actual del candidato (emite un token nuevo)."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)

    if candidato.estado in (EstadoCandidato.CV_APROBADO, EstadoCandidato.EXAMEN_PENDIENTE):
        token = await emitir_token_candidato(candidato.id, candidato.tenant_id, TipoToken.EXAMEN, db)
        await correo_bienvenida_examen(candidato, token)
    elif candidato.estado == EstadoCandidato.ENTREVISTA_PENDIENTE:
        token = await emitir_token_candidato(candidato.id, candidato.tenant_id, TipoToken.ENTREVISTA, db)
        await correo_invitacion_entrevista(candidato, token)
    elif candidato.estado == EstadoCandidato.FINALISTA:
        vacante = await db.get(Vacante, candidato.vacante_id)
        await correo_finalista(candidato, vacante)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estado actual del candidato no tiene un correo de etapa asociado",
        )

    return MensajeResponse(detail="Correo reenviado")


@router.get("/{candidato_id}/notas", response_model=list[NotaResponse])
async def listar_notas_candidato(
    candidato_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NotaCandidato]:
    """Lista las notas internas de un candidato, de la más reciente a la más antigua."""
    await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)

    statement = (
        select(NotaCandidato)
        .where(NotaCandidato.tenant_id == actor.tenant_id, NotaCandidato.candidato_id == candidato_id)
        .order_by(NotaCandidato.created_at.desc())
    )
    result = await db.exec(statement)
    return list(result.all())


@router.post("/{candidato_id}/notas", response_model=NotaResponse, status_code=status.HTTP_201_CREATED)
async def crear_nota_candidato(
    candidato_id: str,
    body: NotaCreateRequest,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotaCandidato:
    """Agrega una nota interna a un candidato."""
    await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)

    nota = NotaCandidato(
        tenant_id=actor.tenant_id,
        candidato_id=candidato_id,
        autor_id=actor.id,
        contenido=body.contenido,
    )
    db.add(nota)
    await db.commit()
    await db.refresh(nota)
    return nota
