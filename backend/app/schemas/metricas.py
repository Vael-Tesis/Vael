"""Schemas de respuesta del dashboard de métricas — /api/metricas/ (RF-A-19, HU-20, doc 14)."""
from datetime import date

from pydantic import BaseModel


class PostulacionPorDia(BaseModel):
    """Candidatos postulados en un día (`Candidato.fecha_postulacion`), dentro del rango pedido."""

    fecha: date
    cantidad: int


class MetricasDashboardResponse(BaseModel):
    """Resumen del dashboard (RF-A-19): fotografía del estado actual más las métricas del
    periodo `desde`/`hasta`.

    `vacantes_por_estado`, `candidatos_por_estado` y `recomendaciones_pendientes_por_etapa`
    son el estado actual del tenant, sin filtrar por fecha. `postulaciones_por_dia`,
    `minutos_promedio_revision` (OE1) y `tasa_concordancia` (M-02) sí se acotan al rango.
    """

    vacantes_por_estado: dict[str, int]
    candidatos_por_estado: dict[str, int]
    recomendaciones_pendientes_por_etapa: dict[str, int]
    postulaciones_por_dia: list[PostulacionPorDia]
    minutos_promedio_revision: float | None
    tasa_concordancia: float | None
