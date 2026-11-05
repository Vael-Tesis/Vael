"""Endpoint del dashboard de métricas — /api/metricas/ (RF-A-19, HU-20, doc 14)."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.candidato import Candidato, EstadoCandidato
from app.models.decision import DecisionCandidato
from app.models.usuario import Usuario
from app.models.vacante import EstadoVacante, Vacante
from app.schemas.metricas import MetricasDashboardResponse, PostulacionPorDia
from app.services.decisiones import ESTADO_POR_CONFIRMAR

router = APIRouter(prefix="/api/metricas", tags=["metricas"])


async def _conteo_por_estado(
    db: AsyncSession, tenant_id: str, modelo: type, columna, estados
) -> dict[str, int]:
    """Candidatos o vacantes del tenant agrupados por estado; incluye los estados sin
    ninguno con 0, para que el frontend no tenga que completarlos."""
    statement = select(columna, func.count()).where(modelo.tenant_id == tenant_id).group_by(columna)
    conteos = {estado: cantidad for estado, cantidad in (await db.exec(statement)).all()}
    return {estado.value: conteos.get(estado, 0) for estado in estados}


async def _recomendaciones_pendientes_por_etapa(db: AsyncSession, tenant_id: str) -> dict[str, int]:
    """Candidatos a la espera de una decisión en cada etapa (los mismos estados de la bandeja
    de recomendaciones y del ranking de finalistas, `services.decisiones.ESTADO_POR_CONFIRMAR`)."""
    estados_interes = list(ESTADO_POR_CONFIRMAR.values())
    statement = (
        select(Candidato.estado, func.count())
        .where(Candidato.tenant_id == tenant_id, Candidato.estado.in_(estados_interes))
        .group_by(Candidato.estado)
    )
    conteos = {estado: cantidad for estado, cantidad in (await db.exec(statement)).all()}
    return {etapa.value: conteos.get(estado, 0) for etapa, estado in ESTADO_POR_CONFIRMAR.items()}


async def _postulaciones_por_dia(
    db: AsyncSession, tenant_id: str, desde: date | None, hasta: date | None
) -> list[PostulacionPorDia]:
    fecha_columna = func.date(Candidato.fecha_postulacion)
    statement = select(fecha_columna, func.count()).where(Candidato.tenant_id == tenant_id)
    if desde is not None:
        statement = statement.where(fecha_columna >= desde)
    if hasta is not None:
        statement = statement.where(fecha_columna <= hasta)
    statement = statement.group_by(fecha_columna).order_by(fecha_columna)
    return [PostulacionPorDia(fecha=fecha, cantidad=cantidad) for fecha, cantidad in (await db.exec(statement)).all()]


def _acotar_por_decidido_en(statement, desde: date | None, hasta: date | None):
    """Filtra decisiones por el día de `decidido_en`, dentro del rango `desde`/`hasta`."""
    fecha_columna = func.date(DecisionCandidato.decidido_en)
    if desde is not None:
        statement = statement.where(fecha_columna >= desde)
    if hasta is not None:
        statement = statement.where(fecha_columna <= hasta)
    return statement


async def _minutos_promedio_revision(
    db: AsyncSession, tenant_id: str, desde: date | None, hasta: date | None
) -> float | None:
    """OE1: promedio de `decidido_en - revision_inicio` en minutos (doc 14), sobre las
    decisiones que registraron cuándo RRHH abrió la recomendación."""
    statement = select(
        func.avg(func.extract("epoch", DecisionCandidato.decidido_en - DecisionCandidato.revision_inicio) / 60)
    ).where(DecisionCandidato.tenant_id == tenant_id, DecisionCandidato.revision_inicio.is_not(None))
    statement = _acotar_por_decidido_en(statement, desde, hasta)
    promedio = (await db.exec(statement)).one()
    return round(float(promedio), 2) if promedio is not None else None


async def _tasa_concordancia(
    db: AsyncSession, tenant_id: str, desde: date | None, hasta: date | None
) -> float | None:
    """M-02: porcentaje de decisiones que coinciden con la recomendación de la IA, sobre las
    decisiones con recomendación (la entrevista sin `score_final` no tiene una, DEC-022)."""
    statement = select(func.count(), func.count().filter(DecisionCandidato.coincide_con_ia.is_(True))).where(
        DecisionCandidato.tenant_id == tenant_id, DecisionCandidato.coincide_con_ia.is_not(None)
    )
    statement = _acotar_por_decidido_en(statement, desde, hasta)
    total, concordantes = (await db.exec(statement)).one()
    return round(concordantes / total * 100, 2) if total else None


@router.get("/dashboard", response_model=MetricasDashboardResponse)
async def dashboard(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    desde: date | None = None,
    hasta: date | None = None,
) -> MetricasDashboardResponse:
    """Resumen del tenant para el dashboard (RF-A-19): vacantes y candidatos por estado,
    recomendaciones pendientes por etapa, postulaciones por día, minutos promedio de revisión
    (OE1) y tasa de concordancia (M-02). `desde`/`hasta` acotan las dos últimas y las
    postulaciones por día; sin ellos, cubren todo el histórico del tenant.
    """
    return MetricasDashboardResponse(
        vacantes_por_estado=await _conteo_por_estado(db, actor.tenant_id, Vacante, Vacante.estado, EstadoVacante),
        candidatos_por_estado=await _conteo_por_estado(db, actor.tenant_id, Candidato, Candidato.estado, EstadoCandidato),
        recomendaciones_pendientes_por_etapa=await _recomendaciones_pendientes_por_etapa(db, actor.tenant_id),
        postulaciones_por_dia=await _postulaciones_por_dia(db, actor.tenant_id, desde, hasta),
        minutos_promedio_revision=await _minutos_promedio_revision(db, actor.tenant_id, desde, hasta),
        tasa_concordancia=await _tasa_concordancia(db, actor.tenant_id, desde, hasta),
    )
