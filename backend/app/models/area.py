"""Modelo: Area."""
from sqlmodel import Field

from app.models.base import TenantBase, TimestampMixin, new_id


class Area(TenantBase, TimestampMixin, table=True):
    """Área o departamento de la empresa cliente, con su propia instrucción de IA."""

    __tablename__ = "areas"

    id: str = Field(default_factory=new_id, primary_key=True)
    nombre: str = Field(nullable=False)
    codigo_corto: str = Field(nullable=False, index=True, max_length=10)
    descripcion: str | None = Field(default=None)
    instruccion_ia: str | None = Field(default=None)
    activa: bool = Field(default=True, nullable=False)
