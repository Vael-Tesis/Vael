"""Modelos: Candidato, Tag, NotaCandidato."""
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TenantBase, TimestampMixin, new_id, utcnow


class EstadoCandidato(str, Enum):
    """Estado del candidato a lo largo del proceso de selección."""

    POSTULADO = "postulado"
    CV_ANALIZANDO = "cv_analizando"
    CV_APROBADO = "cv_aprobado"
    CV_RECHAZADO = "cv_rechazado"
    EXAMEN_PENDIENTE = "examen_pendiente"
    EXAMEN_RENDIDO = "examen_rendido"
    EXAMEN_APROBADO = "examen_aprobado"
    EXAMEN_RECHAZADO = "examen_rechazado"
    ENTREVISTA_PENDIENTE = "entrevista_pendiente"
    ENTREVISTA_REALIZADA = "entrevista_realizada"
    FINALISTA = "finalista"
    CONTRATADO = "contratado"
    DESCARTADO = "descartado"


class ClasificacionIA(str, Enum):
    """Clasificación asignada por la IA tras analizar el CV del candidato."""

    ALTAMENTE_RECOMENDADO = "altamente_recomendado"
    RECOMENDADO = "recomendado"
    REQUIERE_REVISION = "requiere_revision"
    NO_APTO = "no_apto"


class Candidato(TenantBase, TimestampMixin, table=True):
    """Candidato postulante a una vacante y su progreso a través del proceso de selección."""

    __tablename__ = "candidatos"

    id: str = Field(default_factory=new_id, primary_key=True)
    vacante_id: str = Field(nullable=False, index=True, foreign_key="vacantes.id")

    nombre: str = Field(nullable=False)
    apellidos: str = Field(nullable=False)
    email: str = Field(nullable=False, index=True)
    telefono: str | None = Field(default=None)

    linkedin: str | None = Field(default=None)
    github: str | None = Field(default=None)
    portfolio: str | None = Field(default=None)
    cv_url: str | None = Field(default=None)

    estado: EstadoCandidato = Field(default=EstadoCandidato.POSTULADO, nullable=False, index=True)
    es_finalista: bool = Field(default=False, nullable=False)
    pretension_salarial: float | None = Field(default=None)

    score_cv: int | None = Field(default=None)
    match_porcentaje: float | None = Field(default=None)
    clasificacion_ia: ClasificacionIA | None = Field(default=None)
    resumen_ia: str | None = Field(default=None)
    habilidades_detectadas: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    inconsistencias: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    analizado_en: datetime | None = Field(default=None)

    score_final: float | None = Field(default=None)
    fecha_postulacion: datetime = Field(default_factory=utcnow, nullable=False)


class Tag(TenantBase, table=True):
    """Etiqueta libre para clasificar candidatos."""

    __tablename__ = "tags"

    id: str = Field(default_factory=new_id, primary_key=True)
    nombre: str = Field(nullable=False, max_length=50)
    color: str | None = Field(default=None, max_length=20)


class NotaCandidato(TenantBase, table=True):
    """Nota interna dejada por un usuario de RRHH sobre un candidato."""

    __tablename__ = "notas_candidato"

    id: str = Field(default_factory=new_id, primary_key=True)
    candidato_id: str = Field(nullable=False, index=True, foreign_key="candidatos.id")
    autor_id: str = Field(nullable=False, index=True, foreign_key="usuarios.id")
    contenido: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
