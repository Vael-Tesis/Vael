"""Schemas de request y response para la entrevista con EVA — /api/entrevista/."""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.entrevista import EstadoEntrevista, TipoCaptura


class PrioridadPregunta(str, Enum):
    """Prioridad de una pregunta del pool dinámico de la entrevista (sección 10 del CLAUDE.md)."""

    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"


class PreguntaEntrevistaPool(BaseModel):
    """Pregunta del pool dinámico (8-12 preguntas) generado para la entrevista."""

    enunciado: str
    prioridad: PrioridadPregunta


class IniciarEntrevistaResponse(BaseModel):
    """Datos para que el frontend abra la sesión de Gemini Live con EVA."""

    entrevista_id: str
    token_efimero: str
    preguntas: list[PreguntaEntrevistaPool]


class FinalizarEntrevistaRequest(BaseModel):
    """Transcripción final de la entrevista, capturada por el frontend desde Gemini Live."""

    transcripcion: str = Field(min_length=1)
    audio_url: str | None = None
    duracion_minutos: int | None = None


class CapturaEntrevistaResponse(BaseModel):
    """Foto de auditoría guardada durante la entrevista."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    entrevista_id: str
    tipo: TipoCaptura
    imagen_url: str
    timestamp: datetime


class EventoAuditoriaRequest(BaseModel):
    """Evento de auditoría detectado durante la entrevista (catálogo en la sección 11 del CLAUDE.md)."""

    tipo: str = Field(min_length=1)
    detalle: str | None = None


class EntrevistaDetalleResponse(BaseModel):
    """Vista 360° de una entrevista: nota, dimensiones, audio, transcripción y capturas."""

    id: str
    candidato_id: str
    candidato_nombre: str
    candidato_apellidos: str
    vacante_id: str
    estado: EstadoEntrevista
    nota: float | None
    transcripcion: str | None
    audio_url: str | None
    duracion_minutos: int | None
    dimensiones_json: dict[str, Any] | None
    fecha_inicio: datetime | None
    fecha_fin: datetime | None
    capturas: list[CapturaEntrevistaResponse]


class MensajeResponse(BaseModel):
    """Respuesta genérica de confirmación."""

    detail: str
