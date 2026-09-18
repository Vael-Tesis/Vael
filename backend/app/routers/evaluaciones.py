"""Endpoints de exámenes (RRHH) y flujo del candidato con token — /api/evaluaciones/."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_candidate, get_current_candidato, get_current_user
from app.models.area import Area
from app.models.candidato import Candidato
from app.models.evaluacion import Examen, EstadoExamen, EventoAuditoria, PreguntaExamen
from app.models.base import utcnow
from app.models.usuario import Usuario
from app.models.vacante import Vacante
from app.schemas.evaluacion import (
    CandidatoAccesoResponse,
    EventoAuditoriaResponse,
    EventoProctoringRequest,
    ExamenDetalleResponse,
    ExamenResponse,
    FinalizarExamenResponse,
    GuardarRespuestaRequest,
    IniciarExamenResponse,
    MensajeResponse,
    PreguntaExamenPublica,
    PreguntaExamenResponse,
    ProgresoCandidatoResponse,
)
from app.services.examen import calificar_examen, generar_preguntas, registrar_evento

router = APIRouter(prefix="/api/evaluaciones", tags=["evaluaciones"])


def _exigir_tipo_examen(claims: dict[str, Any]) -> None:
    """Verifica que el token de candidato sea de tipo 'examen', o lanza 403."""
    if claims.get("tipo") != "examen":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este token no es de acceso al examen")


async def _obtener_examen_del_candidato(candidato: Candidato, db: AsyncSession) -> Examen:
    """Busca el examen vigente del candidato para su vacante, o lanza 404 si no existe."""
    statement = select(Examen).where(
        Examen.candidato_id == candidato.id,
        Examen.vacante_id == candidato.vacante_id,
    )
    result = await db.exec(statement)
    examen = result.first()

    if examen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay un examen iniciado para este candidato",
        )

    return examen


async def _obtener_examen_del_tenant(examen_id: str, tenant_id: str, db: AsyncSession) -> Examen:
    """Busca un examen por id dentro del tenant actual, o lanza 404 si no existe."""
    statement = select(Examen).where(Examen.id == examen_id, Examen.tenant_id == tenant_id)
    result = await db.exec(statement)
    examen = result.first()

    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen no encontrado")

    return examen


# --- RRHH ---------------------------------------------------------------


@router.get("/examenes", response_model=list[ExamenResponse])
async def listar_examenes(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    candidato_id: str | None = None,
    vacante_id: str | None = None,
    estado: EstadoExamen | None = None,
) -> list[Examen]:
    """Lista los exámenes del tenant, con filtros opcionales por candidato, vacante y estado."""
    statement = select(Examen).where(Examen.tenant_id == actor.tenant_id)

    if candidato_id is not None:
        statement = statement.where(Examen.candidato_id == candidato_id)
    if vacante_id is not None:
        statement = statement.where(Examen.vacante_id == vacante_id)
    if estado is not None:
        statement = statement.where(Examen.estado == estado)

    result = await db.exec(statement)
    return list(result.all())


@router.get("/examenes/{examen_id}", response_model=ExamenDetalleResponse)
async def obtener_examen(
    examen_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamenDetalleResponse:
    """Retorna el detalle de un examen con sus preguntas y respuestas."""
    examen = await _obtener_examen_del_tenant(examen_id, actor.tenant_id, db)

    preguntas_statement = (
        select(PreguntaExamen).where(PreguntaExamen.examen_id == examen.id).order_by(PreguntaExamen.orden)
    )
    preguntas_result = await db.exec(preguntas_statement)
    preguntas = list(preguntas_result.all())

    examen_data = ExamenResponse.model_validate(examen).model_dump()
    return ExamenDetalleResponse(
        **examen_data,
        preguntas=[PreguntaExamenResponse.model_validate(p) for p in preguntas],
    )


@router.get("/examenes/{examen_id}/auditoria", response_model=list[EventoAuditoriaResponse])
async def auditoria_examen(
    examen_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EventoAuditoria]:
    """Lista los eventos de proctoring registrados durante un examen."""
    await _obtener_examen_del_tenant(examen_id, actor.tenant_id, db)

    statement = (
        select(EventoAuditoria)
        .where(EventoAuditoria.examen_id == examen_id, EventoAuditoria.tenant_id == actor.tenant_id)
        .order_by(EventoAuditoria.timestamp)
    )
    result = await db.exec(statement)
    return list(result.all())


# --- Candidato (token de acceso, no usuario RRHH) ------------------------


@router.post("/candidato/acceso", response_model=CandidatoAccesoResponse)
async def acceso_candidato(
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
) -> Candidato:
    """Valida el token de examen del candidato y retorna sus datos básicos."""
    _exigir_tipo_examen(claims)
    return candidato


@router.post("/candidato/examen/iniciar", response_model=IniciarExamenResponse)
async def iniciar_examen(
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IniciarExamenResponse:
    """Genera (o retoma) el examen del candidato con preguntas generadas por Gemini."""
    _exigir_tipo_examen(claims)

    statement = select(Examen).where(
        Examen.candidato_id == candidato.id,
        Examen.vacante_id == candidato.vacante_id,
    )
    result = await db.exec(statement)
    examen = result.first()

    if examen is None:
        vacante = await db.get(Vacante, candidato.vacante_id)
        area = await db.get(Area, vacante.area_id) if vacante is not None else None

        examen = Examen(
            tenant_id=candidato.tenant_id,
            candidato_id=candidato.id,
            vacante_id=candidato.vacante_id,
            estado=EstadoExamen.GENERANDO,
        )
        db.add(examen)
        await db.commit()
        await db.refresh(examen)

        preguntas = await generar_preguntas(candidato, vacante, area)
        for pregunta in preguntas:
            pregunta.tenant_id = candidato.tenant_id
            pregunta.examen_id = examen.id
            db.add(pregunta)

        examen.estado = EstadoExamen.EN_CURSO
        examen.fecha_inicio = utcnow()
        db.add(examen)
        await db.commit()
        await db.refresh(examen)

    preguntas_statement = (
        select(PreguntaExamen).where(PreguntaExamen.examen_id == examen.id).order_by(PreguntaExamen.orden)
    )
    preguntas_result = await db.exec(preguntas_statement)
    preguntas_persistidas = list(preguntas_result.all())

    return IniciarExamenResponse(
        examen_id=examen.id,
        duracion_minutos=examen.duracion_minutos,
        preguntas=[PreguntaExamenPublica.model_validate(p) for p in preguntas_persistidas],
    )


@router.post("/candidato/examen/respuesta", response_model=MensajeResponse)
async def guardar_respuesta_examen(
    body: GuardarRespuestaRequest,
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Guarda (auto-guardado) la respuesta del candidato a una pregunta del examen."""
    _exigir_tipo_examen(claims)

    pregunta = await db.get(PreguntaExamen, body.pregunta_id)
    if pregunta is None or pregunta.tenant_id != candidato.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pregunta no encontrada")

    examen = await db.get(Examen, pregunta.examen_id)
    if examen is None or examen.candidato_id != candidato.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La pregunta no pertenece a tu examen")

    pregunta.respuesta_candidato = body.respuesta
    db.add(pregunta)
    await db.commit()

    return MensajeResponse(detail="Respuesta guardada")


@router.post("/candidato/examen/finalizar", response_model=FinalizarExamenResponse)
async def finalizar_examen(
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinalizarExamenResponse:
    """Cierra el examen del candidato y dispara su calificación (MC automático + IA para abiertas)."""
    _exigir_tipo_examen(claims)
    examen = await _obtener_examen_del_candidato(candidato, db)

    examen.fecha_fin = utcnow()
    examen.estado = EstadoExamen.FINALIZADO
    db.add(examen)
    await db.commit()

    await calificar_examen(examen.id, db)
    await db.refresh(examen)

    return FinalizarExamenResponse(
        nota=examen.nota,
        semaforo=examen.semaforo,
        mensaje="Examen calificado correctamente",
    )


@router.post("/candidato/examen/evento", response_model=MensajeResponse)
async def registrar_evento_examen(
    body: EventoProctoringRequest,
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Registra un evento de proctoring y actualiza el puntaje de riesgo/semáforo del examen."""
    _exigir_tipo_examen(claims)
    examen = await _obtener_examen_del_candidato(candidato, db)

    await registrar_evento(examen.id, candidato.tenant_id, body.tipo, body.detalle, db)

    return MensajeResponse(detail="Evento registrado")


@router.get("/candidato/progreso", response_model=ProgresoCandidatoResponse)
async def progreso_candidato(
    candidato: Annotated[Candidato, Depends(get_current_candidato)],
) -> ProgresoCandidatoResponse:
    """Retorna el estado actual del candidato en su proceso de selección."""
    return ProgresoCandidatoResponse(
        candidato_id=candidato.id,
        estado=candidato.estado,
        es_finalista=candidato.es_finalista,
    )
