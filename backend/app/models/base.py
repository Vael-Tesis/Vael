"""Clases base compartidas por todos los modelos: TenantBase y TimestampMixin."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Retorna la fecha y hora actual en UTC — usada como default de los timestamps."""
    return datetime.now(timezone.utc)


def new_id() -> str:
    """Genera un UUID v4 como string — usado como default de las primary keys."""
    return str(uuid4())


class TenantBase(SQLModel):
    """Mixin que agrega tenant_id (UUID de la empresa cliente) indexado a un modelo.

    Todo modelo que pertenece a un tenant debe heredar de esta clase; ningún query
    sobre estos modelos debe omitir el filtro por tenant_id.
    """

    tenant_id: str = Field(index=True, nullable=False, max_length=36)


class TimestampMixin(SQLModel):
    """Mixin que agrega marcas de tiempo de creación y actualización a un modelo."""

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)
