"""Endpoints de la entrevista con EVA vía Gemini Live — /api/entrevista/."""
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_candidate, get_current_candidato, get_current_user
from app.core.proctoring import CATALOGO_EVENTOS_PROCTORING, EVENTO_DEFAULT
from app.models.base import new_id, utcnow
from app.models.candidato import Candidato
from app.models.entrevista import CapturaAuditoria, EntrevistaIA, EstadoEntrevista, PlantillaEvaluacion, TipoCaptura
from app.models.evaluacion import EventoAuditoria
from app.models.usuario import Usuario
from app.models.vacante import Vacante
from app.schemas.entrevista import (
    CapturaEntrevistaResponse,
    EntrevistaDetalleResponse,
    EntrevistaResponse,
    EventoAuditoriaRequest,
    FinalizarEntrevistaRequest,
    IniciarEntrevistaResponse,
    MensajeResponse,
)
from app.schemas.evaluacion import CandidatoAccesoResponse
from app.services.aws_services import subir_archivo
from app.services.entrevista_ia import (
    analizar_entrevista_candidato,
    generar_pool_preguntas,
    generar_token_efimero_live,
)

router = APIRouter(prefix="/api/entrevista", tags=["entrevista"])


def _exigir_tipo_entrevista(claims: dict[str, Any]) -> None:
    """Verifica que el token de candidato sea de tipo 'entrevista', o lanza 403."""
    if claims.get("tipo") != "entrevista":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este token no es de acceso a la entrevista",
        )


async def _obtener_plantilla_activa(tenant_id: str, db: AsyncSession) -> PlantillaEvaluacion | None:
    """Busca la primera plantilla de evaluación activa del tenant (no hay una plantilla por vacante)."""
    statement = select(PlantillaEvaluacion).where(
        PlantillaEvaluacion.tenant_id == tenant_id,
        PlantillaEvaluacion.activa.is_(True),
    )
    result = await db.exec(statement)
    return result.first()


async def _obtener_entrevista_del_candidato(candidato: Candidato, db: AsyncSession) -> EntrevistaIA:
    """Busca la entrevista vigente del candidato para su vacante, o lanza 404 si no existe."""
    statement = select(EntrevistaIA).where(
        EntrevistaIA.candidato_id == candidato.id,
        EntrevistaIA.vacante_id == candidato.vacante_id,
    )
    result = await db.exec(statement)
    entrevista = result.first()

    if entrevista is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay una entrevista iniciada para este candidato",
        )

    return entrevista


async def _obtener_entrevista_del_tenant(entrevista_id: str, tenant_id: str, db: AsyncSession) -> EntrevistaIA:
    """Busca una entrevista por id dentro del tenant actual, o lanza 404 si no existe."""
    statement = select(EntrevistaIA).where(EntrevistaIA.id == entrevista_id, EntrevistaIA.tenant_id == tenant_id)
    result = await db.exec(statement)
    entrevista = result.first()

    if entrevista is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrevista no encontrada")

    return entrevista


@router.get("", response_model=list[EntrevistaResponse])
async def listar_entrevistas(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    candidato_id: str | None = None,
    vacante_id: str | None = None,
    estado: EstadoEntrevista | None = None,
) -> list[EntrevistaIA]:
    """Lista las entrevistas del tenant, con filtros opcionales por candidato, vacante y estado."""
    statement = select(EntrevistaIA).where(EntrevistaIA.tenant_id == actor.tenant_id)

    if candidato_id is not None:
        statement = statement.where(EntrevistaIA.candidato_id == candidato_id)
    if vacante_id is not None:
        statement = statement.where(EntrevistaIA.vacante_id == vacante_id)
    if estado is not None:
        statement = statement.where(EntrevistaIA.estado == estado)

    result = await db.exec(statement)
    return list(result.all())


@router.post("/acceso", response_model=CandidatoAccesoResponse)
async def acceso_entrevista(
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
) -> Candidato:
    """Valida el token de entrevista del candidato y retorna sus datos básicos."""
    _exigir_tipo_entrevista(claims)
    return candidato


@router.post("/iniciar", response_model=IniciarEntrevistaResponse)
async def iniciar_entrevista(
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IniciarEntrevistaResponse:
    """Genera el token efímero de Gemini Live y el pool dinámico de preguntas para EVA."""
    _exigir_tipo_entrevista(claims)

    statement = select(EntrevistaIA).where(
        EntrevistaIA.candidato_id == candidato.id,
        EntrevistaIA.vacante_id == candidato.vacante_id,
    )
    result = await db.exec(statement)
    entrevista = result.first()

    vacante = await db.get(Vacante, candidato.vacante_id)

    if entrevista is None:
        plantilla = await _obtener_plantilla_activa(candidato.tenant_id, db)

        entrevista = EntrevistaIA(
            tenant_id=candidato.tenant_id,
            candidato_id=candidato.id,
            vacante_id=candidato.vacante_id,
            plantilla_id=plantilla.id if plantilla else None,
            estado=EstadoEntrevista.EN_CURSO,
            fecha_inicio=utcnow(),
        )
        db.add(entrevista)
        await db.commit()
        await db.refresh(entrevista)
    else:
        plantilla = (
            await db.get(PlantillaEvaluacion, entrevista.plantilla_id) if entrevista.plantilla_id else None
        )

    preguntas = await generar_pool_preguntas(candidato, vacante, plantilla)
    token_efimero = await generar_token_efimero_live(candidato, vacante, preguntas)

    return IniciarEntrevistaResponse(
        entrevista_id=entrevista.id,
        token_efimero=token_efimero,
        preguntas=preguntas,
    )


@router.post("/finalizar", response_model=MensajeResponse, status_code=status.HTTP_202_ACCEPTED)
async def finalizar_entrevista(
    body: FinalizarEntrevistaRequest,
    background_tasks: BackgroundTasks,
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Guarda la transcripción de la entrevista y dispara el análisis multidimensional en background."""
    _exigir_tipo_entrevista(claims)
    entrevista = await _obtener_entrevista_del_candidato(candidato, db)

    entrevista.transcripcion = body.transcripcion
    entrevista.audio_url = body.audio_url
    entrevista.duracion_minutos = body.duracion_minutos
    entrevista.fecha_fin = utcnow()
    entrevista.estado = EstadoEntrevista.FINALIZADA
    db.add(entrevista)
    await db.commit()

    background_tasks.add_task(analizar_entrevista_candidato, entrevista.id)

    return MensajeResponse(detail="Entrevista finalizada, análisis en curso")


@router.post("/captura", response_model=CapturaEntrevistaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_captura_entrevista(
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tipo: Annotated[TipoCaptura, Form()],
    imagen: Annotated[UploadFile, File()],
) -> CapturaAuditoria:
    """Sube a S3 una foto de auditoría (identidad, periódica o sospechosa) de la entrevista."""
    _exigir_tipo_entrevista(claims)
    entrevista = await _obtener_entrevista_del_candidato(candidato, db)

    contenido = await imagen.read()
    clave = f"capturas/{candidato.tenant_id}/{entrevista.id}/{new_id()}_{imagen.filename or 'captura.jpg'}"
    imagen_url = await subir_archivo(contenido, clave, imagen.content_type or "image/jpeg")

    captura = CapturaAuditoria(
        tenant_id=candidato.tenant_id,
        entrevista_id=entrevista.id,
        tipo=tipo,
        imagen_url=imagen_url,
    )
    db.add(captura)
    await db.commit()
    await db.refresh(captura)
    return captura


@router.post("/evento", response_model=MensajeResponse)
async def registrar_evento_entrevista(
    body: EventoAuditoriaRequest,
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Registra un evento de auditoría de la entrevista (p. ej. multiples_voces, sin_rostro).

    A diferencia del examen, EntrevistaIA no tiene puntaje_riesgo/semaforo propio en el
    modelo — el evento queda registrado para auditoría, pero sin acumulado en vivo.
    """
    _exigir_tipo_entrevista(claims)
    entrevista = await _obtener_entrevista_del_candidato(candidato, db)

    severidad, _ = CATALOGO_EVENTOS_PROCTORING.get(body.tipo, EVENTO_DEFAULT)

    evento = EventoAuditoria(
        tenant_id=candidato.tenant_id,
        entrevista_id=entrevista.id,
        tipo=body.tipo,
        severidad=severidad,
        detalle=body.detalle,
    )
    db.add(evento)
    await db.commit()

    return MensajeResponse(detail="Evento registrado")


@router.get("/detalle/{entrevista_id}", response_model=EntrevistaDetalleResponse)
async def detalle_entrevista(
    entrevista_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EntrevistaDetalleResponse:
    """Vista 360° de una entrevista: nota, dimensiones, audio, transcripción y capturas."""
    entrevista = await _obtener_entrevista_del_tenant(entrevista_id, actor.tenant_id, db)
    candidato = await db.get(Candidato, entrevista.candidato_id)

    capturas_statement = (
        select(CapturaAuditoria)
        .where(CapturaAuditoria.entrevista_id == entrevista.id)
        .order_by(CapturaAuditoria.timestamp)
    )
    capturas_result = await db.exec(capturas_statement)
    capturas = list(capturas_result.all())

    return EntrevistaDetalleResponse(
        id=entrevista.id,
        candidato_id=entrevista.candidato_id,
        candidato_nombre=candidato.nombre if candidato else "",
        candidato_apellidos=candidato.apellidos if candidato else "",
        vacante_id=entrevista.vacante_id,
        estado=entrevista.estado,
        nota=entrevista.nota,
        transcripcion=entrevista.transcripcion,
        audio_url=entrevista.audio_url,
        duracion_minutos=entrevista.duracion_minutos,
        dimensiones_json=entrevista.dimensiones_json,
        fecha_inicio=entrevista.fecha_inicio,
        fecha_fin=entrevista.fecha_fin,
        capturas=[CapturaEntrevistaResponse.model_validate(c) for c in capturas],
    )
