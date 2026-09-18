"""Schemas de request y response para candidatos — /api/candidatos/."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.candidato import ClasificacionIA, EstadoCandidato


class CandidatoCreateRequest(BaseModel):
    """Datos para el registro manual de un candidato."""

    vacante_id: str
    nombre: str = Field(min_length=1)
    apellidos: str = Field(min_length=1)
    email: EmailStr
    telefono: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    cv_url: str | None = None
    pretension_salarial: float | None = None


class CandidatoUpdateRequest(BaseModel):
    """Datos editables de un candidato — todos opcionales (actualización parcial).

    No incluye vacante_id, estado, es_finalista ni los campos calculados por IA:
    tienen endpoints/servicios dedicados para no pisarse con el análisis automático.
    """

    nombre: str | None = None
    apellidos: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    cv_url: str | None = None
    pretension_salarial: float | None = None


class CandidatoResponse(BaseModel):
    """Representación completa de un candidato."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    vacante_id: str
    nombre: str
    apellidos: str
    email: EmailStr
    telefono: str | None

    linkedin: str | None
    github: str | None
    portfolio: str | None
    cv_url: str | None

    estado: EstadoCandidato
    es_finalista: bool
    pretension_salarial: float | None

    score_cv: int | None
    match_porcentaje: float | None
    clasificacion_ia: ClasificacionIA | None
    resumen_ia: str | None
    habilidades_detectadas: list[str]
    inconsistencias: list[str]
    analizado_en: datetime | None

    score_final: float | None
    fecha_postulacion: datetime
    created_at: datetime
    updated_at: datetime


class CambiarEstadoRequest(BaseModel):
    """Nuevo estado a asignar manualmente a un candidato."""

    estado: EstadoCandidato


class NotaCreateRequest(BaseModel):
    """Contenido de una nueva nota interna sobre un candidato."""

    contenido: str = Field(min_length=1)


class NotaResponse(BaseModel):
    """Nota interna dejada por un usuario RRHH sobre un candidato."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    candidato_id: str
    autor_id: str
    contenido: str
    created_at: datetime


class CargaMasivaResponse(BaseModel):
    """Resumen de una carga masiva de CVs."""

    creados: int
    candidato_ids: list[str]


class MensajeResponse(BaseModel):
    """Respuesta genérica de confirmación."""

    detail: str
