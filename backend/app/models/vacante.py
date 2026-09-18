"""Modelo: Vacante."""
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TenantBase, TimestampMixin, new_id


class NivelExperiencia(str, Enum):
    """Nivel de experiencia requerido para una vacante."""

    PRACTICANTE = "practicante"
    JUNIOR = "junior"
    SEMI_SENIOR = "semi_senior"
    SENIOR = "senior"
    LIDER = "lider"


class Modalidad(str, Enum):
    """Modalidad de trabajo de una vacante."""

    PRESENCIAL = "presencial"
    REMOTO = "remoto"
    HIBRIDO = "hibrido"


class TipoContrato(str, Enum):
    """Tipo de contrato ofrecido en una vacante."""

    INDEFINIDO = "indefinido"
    PLAZO_FIJO = "plazo_fijo"
    PRACTICAS = "practicas"
    FREELANCE = "freelance"
    PART_TIME = "part_time"


class EstadoVacante(str, Enum):
    """Estado del ciclo de vida de una vacante."""

    BORRADOR = "borrador"
    ABIERTA = "abierta"
    PAUSADA = "pausada"
    CERRADA = "cerrada"


class PrioridadVacante(str, Enum):
    """Prioridad de cobertura de una vacante."""

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class Vacante(TenantBase, TimestampMixin, table=True):
    """Vacante publicada por una empresa cliente para un área específica."""

    __tablename__ = "vacantes"

    id: str = Field(default_factory=new_id, primary_key=True)
    area_id: str = Field(nullable=False, index=True, foreign_key="areas.id")
    codigo: str = Field(nullable=False, unique=True, index=True, max_length=30)  # ej: TI-2026-001
    titulo: str = Field(nullable=False)

    descripcion: str | None = Field(default=None)
    responsabilidades: str | None = Field(default=None)
    requisitos: str | None = Field(default=None)
    requisitos_deseables: str | None = Field(default=None)
    beneficios: str | None = Field(default=None)
    habilidades: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    tecnologias: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    nivel_experiencia: NivelExperiencia | None = Field(default=None)
    anios_experiencia: int | None = Field(default=None)
    modalidad: Modalidad | None = Field(default=None)
    tipo_contrato: TipoContrato | None = Field(default=None)

    ciudad: str | None = Field(default=None)
    pais: str | None = Field(default=None)
    salario_minimo: float | None = Field(default=None)
    salario_maximo: float | None = Field(default=None)
    moneda: str | None = Field(default="PEN", max_length=3)
    mostrar_salario: bool = Field(default=False, nullable=False)

    confidencial: bool = Field(default=False, nullable=False)
    estado: EstadoVacante = Field(default=EstadoVacante.BORRADOR, nullable=False, index=True)
    prioridad: PrioridadVacante = Field(default=PrioridadVacante.MEDIA, nullable=False)
    fecha_limite: datetime | None = Field(default=None)

    jefe_directo: str | None = Field(default=None)
    solicitante: str | None = Field(default=None)
    cantidad_posiciones: int = Field(default=1, nullable=False)

    score_cv_minimo: int = Field(default=60, nullable=False)
    nota_minima_examen: int = Field(default=13, nullable=False)
    top_candidatos_finalistas: int = Field(default=5, nullable=False)
    instruccion_ia_extra: str | None = Field(default=None)
