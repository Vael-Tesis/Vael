"""Clases base compartidas por todos los modelos: TenantBase y TimestampMixin."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Retorna la fecha y hora actual en UTC, sin tzinfo (naive) — las columnas datetime
    se crean como TIMESTAMP WITHOUT TIME ZONE; un valor aware aquí revienta cualquier
    comparación/resta contra lo leído de la base con 'can't subtract offset-naive and
    offset-aware datetimes'. Usada como default de todos los timestamps del proyecto."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
