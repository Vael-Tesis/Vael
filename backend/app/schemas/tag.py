"""Schemas de etiquetas — /api/tags/ y /api/candidatos/{id}/tags (DEV-A-01, HU-13)."""
from pydantic import BaseModel, ConfigDict, Field

_COLOR_HEX = r"^#[0-9A-Fa-f]{6}$"


class TagCreateRequest(BaseModel):
    """Nueva etiqueta de la empresa."""

    nombre: str = Field(min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=_COLOR_HEX, description="Color en formato #RRGGBB")


class TagUpdateRequest(BaseModel):
    """Datos editables de una etiqueta — todos opcionales."""

    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=_COLOR_HEX)


class TagResponse(BaseModel):
    """Etiqueta de la empresa."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    color: str | None


class AsignarTagRequest(BaseModel):
    """Etiqueta a asignar a un candidato."""

    tag_id: str
