"""Modelos: EntrevistaIA, PlantillaEvaluacion, DimensionEvaluacion, CapturaAuditoria."""
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TenantBase, new_id, utcnow


class EstadoEntrevista(str, Enum):
    """Estado de la entrevista conversacional con EVA."""

    PENDIENTE = "pendiente"
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"
    EXPIRADA = "expirada"


class TipoCaptura(str, Enum):
    """Tipo de foto de auditoría tomada durante la entrevista."""

    IDENTIDAD = "identidad"
    PERIODICA = "periodica"
    SOSPECHOSA = "sospechosa"


class EntrevistaIA(TenantBase, table=True):
    """Entrevista conversacional por voz con EVA, sobre Gemini Live API."""

    __tablename__ = "entrevistas_ia"

    id: str = Field(default_factory=new_id, primary_key=True)
    candidato_id: str = Field(nullable=False, index=True, foreign_key="candidatos.id")
    vacante_id: str = Field(nullable=False, index=True, foreign_key="vacantes.id")
    plantilla_id: str | None = Field(default=None, index=True, foreign_key="plantillas_evaluacion.id")

    estado: EstadoEntrevista = Field(default=EstadoEntrevista.PENDIENTE, nullable=False, index=True)
    nota: float | None = Field(default=None)
    transcripcion: str | None = Field(default=None)
    audio_url: str | None = Field(default=None)
    duracion_minutos: int | None = Field(default=None)
    dimensiones_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    fecha_inicio: datetime | None = Field(default=None)
    fecha_fin: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class PlantillaEvaluacion(TenantBase, table=True):
    """Plantilla de evaluación con las dimensiones a calificar en la entrevista."""

    __tablename__ = "plantillas_evaluacion"

    id: str = Field(default_factory=new_id, primary_key=True)
    nombre: str = Field(nullable=False)
    descripcion: str | None = Field(default=None)
    activa: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class DimensionEvaluacion(TenantBase, table=True):
    """Dimensión individual evaluada dentro de una plantilla de evaluación."""

    __tablename__ = "dimensiones_evaluacion"

    id: str = Field(default_factory=new_id, primary_key=True)
    plantilla_id: str = Field(nullable=False, index=True, foreign_key="plantillas_evaluacion.id")
    nombre: str = Field(nullable=False)
    descripcion: str | None = Field(default=None)
    peso: float = Field(nullable=False)
    puntaje_maximo: float = Field(default=20.0, nullable=False)


class CapturaAuditoria(TenantBase, table=True):
    """Foto de auditoría (identidad, periódica o sospechosa) tomada durante la entrevista."""

    __tablename__ = "capturas_auditoria"

    id: str = Field(default_factory=new_id, primary_key=True)
    entrevista_id: str = Field(nullable=False, index=True, foreign_key="entrevistas_ia.id")
    tipo: TipoCaptura = Field(nullable=False)
    imagen_url: str = Field(nullable=False)
    timestamp: datetime = Field(default_factory=utcnow, nullable=False)
