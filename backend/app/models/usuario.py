"""Modelos: Usuario, Empresa, TokenAcceso."""
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from app.models.base import TenantBase, TimestampMixin, new_id, utcnow


class RolUsuario(str, Enum):
    """Roles posibles de un usuario RRHH dentro de un tenant."""

    ADMIN = "admin"
    RECLUTADOR = "reclutador"
    EVALUADOR = "evaluador"
    GERENTE = "gerente"


class TipoToken(str, Enum):
    """Etapa del proceso a la que da acceso un TokenAcceso."""

    EXAMEN = "examen"
    ENTREVISTA = "entrevista"


class Empresa(SQLModel, table=True):
    """Empresa cliente (tenant) de la plataforma. No hereda TenantBase: ella ES el tenant."""

    __tablename__ = "empresas"

    id: str = Field(default_factory=new_id, primary_key=True)
    tenant_id: str = Field(unique=True, index=True, nullable=False, max_length=36)
    nombre: str = Field(nullable=False)
    logo_url: str | None = Field(default=None)
    activa: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class Usuario(TenantBase, TimestampMixin, table=True):
    """Usuario del panel de RRHH — personal de la empresa cliente (tenant)."""

    __tablename__ = "usuarios"

    id: str = Field(default_factory=new_id, primary_key=True)
    nombre: str = Field(nullable=False)
    apellidos: str = Field(nullable=False)
    email: str = Field(nullable=False, unique=True, index=True, max_length=255)
    password_hash: str = Field(nullable=False)
    rol: RolUsuario = Field(nullable=False)
    telefono: str | None = Field(default=None)
    activo: bool = Field(default=True, nullable=False)


class TokenAcceso(TenantBase, table=True):
    """Token de acceso de un candidato a una etapa del proceso (examen o entrevista)."""

    __tablename__ = "tokens_acceso"

    id: str = Field(default_factory=new_id, primary_key=True)
    candidato_id: str = Field(nullable=False, index=True, foreign_key="candidatos.id")
    token: str = Field(nullable=False, unique=True, index=True)
    codigo_corto: str = Field(nullable=False, unique=True, max_length=14)
    tipo: TipoToken = Field(nullable=False)
    expira_en: datetime = Field(nullable=False)
    usado: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
