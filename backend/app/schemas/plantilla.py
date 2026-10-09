"""Schemas de request y response para plantillas de evaluación — /api/plantillas/."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DimensionCreateRequest(BaseModel):
    """Datos de una dimensión a evaluar dentro de una plantilla."""

    nombre: str = Field(min_length=1)
    descripcion: str | None = None
    peso: float = Field(gt=0)
    puntaje_maximo: float = 20.0


class DimensionUpdateRequest(BaseModel):
    """Datos editables de una dimensión — todos opcionales (actualización parcial)."""

    nombre: str | None = None
    descripcion: str | None = None
    peso: float | None = Field(default=None, gt=0)
    puntaje_maximo: float | None = None


class DimensionResponse(BaseModel):
    """Representación completa de una dimensión de evaluación."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    plantilla_id: str
    nombre: str
    descripcion: str | None
    peso: float
    puntaje_maximo: float


class PlantillaCreateRequest(BaseModel):
    """Datos para crear una plantilla de evaluación, con sus dimensiones iniciales."""

    nombre: str = Field(min_length=1)
    descripcion: str | None = None
    activa: bool = True
    dimensiones: list[DimensionCreateRequest] = Field(default_factory=list)


class PlantillaUpdateRequest(BaseModel):
    """Datos editables de una plantilla — todos opcionales (actualización parcial).

    No incluye dimensiones: se administran con los endpoints dedicados de
    /api/plantillas/{id}/dimensiones para no pisar altas/bajas concurrentes.
    """

    nombre: str | None = None
    descripcion: str | None = None
    activa: bool | None = None


class PlantillaResponse(BaseModel):
    """Representación de una plantilla, sin el detalle de sus dimensiones."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    nombre: str
    descripcion: str | None
    activa: bool
    created_at: datetime


class PlantillaDetalleResponse(PlantillaResponse):
    """Plantilla con el detalle completo de sus dimensiones."""

    dimensiones: list[DimensionResponse]


class MensajeResponse(BaseModel):
    """Respuesta genérica de confirmación."""

    detail: str
