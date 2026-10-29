"""Endpoints de gestión de candidatos y ranking — /api/candidatos/."""
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.despacho import TipoTarea, despachar_tarea
from app.core.dependencies import get_current_user, require_rol
from app.core.security import emitir_token_candidato
from app.models.base import new_id, utcnow
from app.models.candidato import Candidato, CandidatoTag, ClasificacionIA, EstadoCandidato, NotaCandidato, Tag
from app.models.entrevista import EntrevistaIA
from app.models.evaluacion import Examen
from app.models.usuario import Empresa, RolUsuario, TipoToken, Usuario
from app.models.vacante import Vacante
from app.models.decision import DecisionCandidato, EtapaDecision
from app.schemas.candidato import (
    CambiarEstadoRequest,
    CandidatoResponse,
    CandidatoUpdateRequest,
    ArchivoFallido,
    CargaMasivaResponse,
    MensajeResponse,
    NotaCreateRequest,
    NotaResponse,
    RankingCandidatoResponse,
)
from app.schemas.decision import (
    CandidatoDetalleResponse,
    DecisionLoteRequest,
    DecisionRequest,
    DecisionResponse,
    RecomendacionPendienteResponse,
)
from app.schemas.tag import AsignarTagRequest, TagResponse
from app.services import candidatos as servicio_candidatos
from app.services import decisiones as servicio_decisiones
from app.services.aws_services import subir_archivo
from app.services.correos import (
    ESTADOS_DESCARTE,
    correo_bienvenida_examen,
    correo_cierre_proceso,
    correo_finalista,
    correo_invitacion_entrevista,
)

router = APIRouter(prefix="/api/candidatos", tags=["candidatos"])
logger = logging.getLogger(__name__)

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


def _como_http(error: servicio_decisiones.ErrorDecision | servicio_candidatos.ErrorCandidatos) -> HTTPException:
    return HTTPException(status_code=error.codigo, detail=error.detalle)


async def _decisiones_response(decisiones: list[DecisionCandidato], tenant_id: str, db: AsyncSession) -> list[DecisionResponse]:
    """Decisiones con el nombre de quien decidió (CA-16)."""
    ids = {d.decidido_por for d in decisiones}
    autores = {}
    if ids:
        statement = select(Usuario).where(Usuario.tenant_id == tenant_id, Usuario.id.in_(ids))
        autores = {u.id: f"{u.nombre} {u.apellidos}" for u in (await db.exec(statement)).all()}
    respuesta = []
    for decision in decisiones:
        fila = DecisionResponse.model_validate(decision)
        fila.decidido_por_nombre = autores.get(decision.decidido_por)
        respuesta.append(fila)
    return respuesta


def _nota_response(nota: NotaCandidato, autor: Usuario | None) -> NotaResponse:
    respuesta = NotaResponse.model_validate(nota)
    respuesta.autor_nombre = f"{autor.nombre} {autor.apellidos}" if autor else None
    return respuesta


@router.get("", response_model=list[CandidatoResponse])
async def listar_candidatos(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    vacante_id: str | None = None,
    estado: EstadoCandidato | None = None,
    clasificacion_ia: ClasificacionIA | None = None,
    tag_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Candidato]:
    """Lista los candidatos del tenant, con filtros opcionales por vacante, estado, clasificación IA y etiqueta."""
    statement = select(Candidato).where(Candidato.tenant_id == actor.tenant_id)

    if vacante_id is not None:
        statement = statement.where(Candidato.vacante_id == vacante_id)
    if estado is not None:
        statement = statement.where(Candidato.estado == estado)
    if clasificacion_ia is not None:
        statement = statement.where(Candidato.clasificacion_ia == clasificacion_ia)
    if tag_id is not None:
        con_tag = select(CandidatoTag.candidato_id).where(
            CandidatoTag.tenant_id == actor.tenant_id, CandidatoTag.tag_id == tag_id
        )
        statement = statement.where(Candidato.id.in_(con_tag))

    statement = statement.offset(skip).limit(limit)

    result = await db.exec(statement)
    return list(result.all())


@router.post("", response_model=CandidatoResponse, status_code=status.HTTP_201_CREATED)
async def crear_candidato(
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
    motivo = servicio_candidatos.motivo_de_rechazo_cv(cv.filename, contenido)
    if motivo is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=motivo)
    clave = f"cvs/{actor.tenant_id}/{vacante_id}/{new_id()}_{cv.filename}"
    try:
        cv_url = await subir_archivo(contenido, clave, "application/pdf")
    except Exception as exc:
        logger.exception("No se pudo subir el CV a S3", extra={"tenant_id": actor.tenant_id})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No se pudo guardar el CV; intenta de nuevo") from exc

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

    await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": candidato.tenant_id, "candidato_id": candidato.id})
    return candidato


@router.get("/ranking", response_model=list[RankingCandidatoResponse])
async def ranking_candidatos(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    vacante_id: str,
) -> list[RankingCandidatoResponse]:
    """Ranking de candidatos de una vacante, ordenado por score_final descendente (RF-A-14).

    Los procesos incompletos (sin score_final) aparecen aparte, al final y sin recomendación.
    Incluye la nota de examen y de entrevista de cada candidato (si ya las rindió), para el
    desglose de las tres componentes del score, y la recomendación de finalistas de la etapa
    entrevista (DEC-022), según `top_candidatos_finalistas` de la vacante.
    """
    vacante = await db.get(Vacante, vacante_id)
    if vacante is None or vacante.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")

    completos = await servicio_decisiones.ranking_vacante(vacante_id, actor.tenant_id, db)
    recomendaciones = servicio_decisiones.recomendaciones_finalistas(completos, vacante.top_candidatos_finalistas)

    incompletos_statement = select(Candidato).where(
        Candidato.tenant_id == actor.tenant_id,
        Candidato.vacante_id == vacante_id,
        Candidato.score_final.is_(None),
    )
    incompletos = list((await db.exec(incompletos_statement.order_by(Candidato.fecha_postulacion))).all())

    candidatos = completos + incompletos
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
            proceso_completo=c.score_final is not None,
            recomendacion_finalista=recomendaciones.get(c.id),
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
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    vacante_id: Annotated[str, Form()],
    archivos: Annotated[list[UploadFile], File()],
) -> CargaMasivaResponse:
    """Sube múltiples CVs para una vacante: crea un candidato por archivo y dispara su análisis IA.

    Informa qué archivos fallaron y por qué (CA-11): no PDF, vacío, más de 10 MB, PDF dañado
    o error al guardarlo. Como el CV recién se analiza en segundo plano, nombre, apellidos y
    correo quedan con un valor provisional hasta que RRHH los corrija.
    """
    vacante = await db.get(Vacante, vacante_id)
    if vacante is None or vacante.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")

    candidato_ids: list[str] = []
    fallidos: list[ArchivoFallido] = []

    for archivo in archivos:
        nombre_archivo = archivo.filename or "sin nombre"
        contenido = await archivo.read()
        motivo = servicio_candidatos.motivo_de_rechazo_cv(archivo.filename, contenido)
        if motivo is not None:
            fallidos.append(ArchivoFallido(nombre=nombre_archivo, motivo=motivo))
            continue
        clave = f"cvs/{actor.tenant_id}/{vacante_id}/{new_id()}_{archivo.filename}"
        try:
            cv_url = await subir_archivo(contenido, clave, "application/pdf")
        except Exception:
            logger.exception("No se pudo subir el CV %s a S3", nombre_archivo, extra={"tenant_id": actor.tenant_id})
            fallidos.append(ArchivoFallido(nombre=nombre_archivo, motivo="No se pudo guardar el archivo; intenta de nuevo"))
            continue

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
        await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": candidato.tenant_id, "candidato_id": candidato.id})

    return CargaMasivaResponse(creados=len(candidato_ids), candidato_ids=candidato_ids, fallidos=fallidos)


@router.get("/por-confirmar", response_model=list[RecomendacionPendienteResponse])
async def bandeja_por_confirmar(
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    vacante_id: str | None = None,
    etapa: EtapaDecision | None = None,
) -> list[RecomendacionPendienteResponse]:
    """Bandeja de recomendaciones de la IA pendientes de decisión humana (DEC-009, HU-15)."""
    pendientes = await servicio_decisiones.recomendaciones_pendientes(
        actor.tenant_id, db, vacante_id=vacante_id, etapa=etapa
    )
    return [
        RecomendacionPendienteResponse(
            candidato=CandidatoResponse.model_validate(candidato),
            etapa=recomendacion.etapa,
            recomendacion_ia=recomendacion.recomendacion,
            puntaje=recomendacion.puntaje,
            umbral=recomendacion.umbral,
            justificacion_ia=recomendacion.justificacion,
            semaforo=semaforo,
        )
        for candidato, recomendacion, semaforo in pendientes
    ]


@router.post("/decisiones/lote", response_model=list[DecisionResponse])
async def decidir_en_lote(
    body: DecisionLoteRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DecisionCandidato]:
    """Confirma varias recomendaciones de una etapa a la vez.

    Solo acepta decisiones que coinciden con la IA; si una no cumple, responde 422 y no
    ejecuta ninguna (DEC-009, punto 4).
    """
    try:
        return await servicio_decisiones.registrar_decisiones_lote(
            body.etapa,
            [(item.candidato_id, item.decision) for item in body.decisiones],
            body.revision_inicio,
            actor,
            db,
        )
    except servicio_decisiones.ErrorDecision as error:
        raise _como_http(error) from error


@router.get("/{candidato_id}", response_model=CandidatoDetalleResponse)
async def obtener_candidato(
    candidato_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidatoDetalleResponse:
    """Retorna el detalle completo de un candidato, con su historial de decisiones (HU-16)."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)
    historial = await servicio_decisiones.historial(candidato.id, actor.tenant_id, db)
    etiquetas = await servicio_candidatos.etiquetas_de(candidato.id, actor.tenant_id, db)
    return CandidatoDetalleResponse(
        **CandidatoResponse.model_validate(candidato).model_dump(),
        decisiones=await _decisiones_response(historial, actor.tenant_id, db),
        tags=[TagResponse.model_validate(t) for t in etiquetas],
    )


@router.post("/{candidato_id}/decision", response_model=DecisionResponse)
async def decidir_candidato(
    candidato_id: str,
    body: DecisionRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DecisionCandidato:
    """Registra la decisión de RRHH sobre la etapa pendiente y ejecuta su efecto (DEC-009, DEC-013).

    Avanzar: estado, token y correo de la etapa siguiente. Descartar: estado y un único correo
    de cierre. Una decisión contraria a la IA sin justificacion_humana responde 422. Repetir la
    decisión vigente no duplica nada; cambiarla la revierte con una fila nueva (reemplaza_a).
    """
    try:
        return await servicio_decisiones.registrar_decision(
            candidato_id,
            servicio_decisiones.DecisionSolicitada(
                body.etapa, body.decision, body.justificacion_humana, body.revision_inicio
            ),
            actor,
            db,
        )
    except servicio_decisiones.ErrorDecision as error:
        raise _como_http(error) from error


@router.get("/{candidato_id}/decisiones", response_model=list[DecisionResponse])
async def historial_decisiones(
    candidato_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DecisionResponse]:
    """Historial de decisiones del candidato, en orden cronológico, con el nombre de quien decidió (HU-16, OE3)."""
    await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)
    historial = await servicio_decisiones.historial(candidato_id, actor.tenant_id, db)
    return await _decisiones_response(historial, actor.tenant_id, db)


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
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Dispara el análisis IA del CV de un candidato en background y responde de inmediato."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)

    candidato.estado = EstadoCandidato.CV_ANALIZANDO
    candidato.updated_at = utcnow()
    db.add(candidato)
    await db.commit()

    await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": candidato.tenant_id, "candidato_id": candidato.id})

    return MensajeResponse(detail="Análisis de CV en curso")


@router.post("/{candidato_id}/cambiar-estado", response_model=CandidatoResponse)
async def cambiar_estado_candidato(
    candidato_id: str,
    body: CambiarEstadoRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Candidato:
    """Cambia manualmente el estado de un candidato.

    No asigna estados de avance ni de descarte: esos solo se alcanzan con una decisión humana
    registrada en POST /{candidato_id}/decision (DEC-009, punto 5).
    """
    if body.estado in servicio_decisiones.ESTADOS_DE_DECISION_HUMANA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El estado {body.estado.value} solo se asigna con una decisión humana (POST /decision)",
        )
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)
    candidato.estado = body.estado
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
    """Reenvía el correo de la etapa actual del candidato (emite un token nuevo si corresponde).

    A un candidato descartado solo se le reenvía el correo de cierre (DEC-013).
    """
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)

    if candidato.estado in (EstadoCandidato.CV_APROBADO, EstadoCandidato.EXAMEN_PENDIENTE):
        token = await emitir_token_candidato(candidato.id, candidato.tenant_id, TipoToken.EXAMEN, db)
        await correo_bienvenida_examen(candidato, token)
    elif candidato.estado in (EstadoCandidato.EXAMEN_APROBADO, EstadoCandidato.ENTREVISTA_PENDIENTE):
        token = await emitir_token_candidato(candidato.id, candidato.tenant_id, TipoToken.ENTREVISTA, db)
        await correo_invitacion_entrevista(candidato, token)
    elif candidato.estado == EstadoCandidato.FINALISTA:
        vacante = await db.get(Vacante, candidato.vacante_id)
        await correo_finalista(candidato, vacante)
    elif candidato.estado in ESTADOS_DESCARTE:
        # A un descartado solo se le reenvía el correo de cierre (DEC-013)
        vacante = await db.get(Vacante, candidato.vacante_id)
        empresa = (await db.exec(select(Empresa).where(Empresa.tenant_id == actor.tenant_id))).first()
        await correo_cierre_proceso(candidato, vacante, empresa)
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
) -> list[NotaResponse]:
    """Lista las notas internas de un candidato, de la más reciente a la más antigua, con su autor."""
    await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)

    statement = (
        select(NotaCandidato, Usuario)
        .join(Usuario, Usuario.id == NotaCandidato.autor_id)
        .where(NotaCandidato.tenant_id == actor.tenant_id, NotaCandidato.candidato_id == candidato_id)
        .order_by(NotaCandidato.created_at.desc())
    )
    result = await db.exec(statement)
    return [_nota_response(nota, autor) for nota, autor in result.all()]


@router.post("/{candidato_id}/notas", response_model=NotaResponse, status_code=status.HTTP_201_CREATED)
async def crear_nota_candidato(
    candidato_id: str,
    body: NotaCreateRequest,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotaResponse:
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
    return _nota_response(nota, actor)


@router.put("/{candidato_id}/notas/{nota_id}", response_model=NotaResponse)
async def editar_nota_candidato(
    candidato_id: str,
    nota_id: str,
    body: NotaCreateRequest,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotaResponse:
    """Edita una nota propia; solo el autor puede hacerlo (HU-13)."""
    try:
        nota = await servicio_candidatos.editar_nota(candidato_id, nota_id, body.contenido, actor, db)
    except servicio_candidatos.ErrorCandidatos as error:
        raise _como_http(error) from error
    return _nota_response(nota, actor)


@router.delete("/{candidato_id}/notas/{nota_id}", response_model=MensajeResponse)
async def eliminar_nota_candidato(
    candidato_id: str,
    nota_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Elimina una nota; puede hacerlo su autor o un admin (HU-13)."""
    try:
        await servicio_candidatos.eliminar_nota(candidato_id, nota_id, actor, db)
    except servicio_candidatos.ErrorCandidatos as error:
        raise _como_http(error) from error
    return MensajeResponse(detail="Nota eliminada")


@router.post("/{candidato_id}/tags", response_model=list[TagResponse])
async def asignar_tag_candidato(
    candidato_id: str,
    body: AsignarTagRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Tag]:
    """Asigna una etiqueta al candidato (idempotente) y devuelve sus etiquetas."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)
    try:
        return await servicio_candidatos.asignar_etiqueta(candidato, body.tag_id, db)
    except servicio_candidatos.ErrorCandidatos as error:
        raise _como_http(error) from error


@router.delete("/{candidato_id}/tags/{tag_id}", response_model=list[TagResponse])
async def quitar_tag_candidato(
    candidato_id: str,
    tag_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Tag]:
    """Quita una etiqueta del candidato y devuelve las que le quedan."""
    candidato = await _obtener_candidato_del_tenant(candidato_id, actor.tenant_id, db)
    try:
        return await servicio_candidatos.quitar_etiqueta(candidato, tag_id, db)
    except servicio_candidatos.ErrorCandidatos as error:
        raise _como_http(error) from error
