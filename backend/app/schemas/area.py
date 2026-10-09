"""Schemas de request y response para áreas — /api/areas/."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AreaCreateRequest(BaseModel):
    """Datos para crear un área o departamento."""

    nombre: str = Field(min_length=1)
    codigo_corto: str = Field(min_length=1, max_length=10)
    descripcion: str | None = None
    instruccion_ia: str | None = None


class AreaUpdateRequest(BaseModel):
    """Datos editables de un área — todos opcionales (actualización parcial)."""

    nombre: str | None = None
    codigo_corto: str | None = Field(default=None, max_length=10)
    descripcion: str | None = None
    instruccion_ia: str | None = None
    activa: bool | None = None


class AreaResponse(BaseModel):
    """Representación completa de un área."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    nombre: str
    codigo_corto: str
    descripcion: str | None
    instruccion_ia: str | None
    activa: bool
    created_at: datetime
    updated_at: datetime


class MensajeResponse(BaseModel):
    """Respuesta genérica de confirmación."""

    detail: str
