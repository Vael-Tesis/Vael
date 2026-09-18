"""Schemas de request y response para evaluaciones (exámenes) — /api/evaluaciones/."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.candidato import EstadoCandidato
from app.models.evaluacion import EstadoExamen, SemaforoExamen, SeveridadEvento, TipoPregunta


class PreguntaExamenPublica(BaseModel):
    """Pregunta de examen tal como la ve el candidato — nunca incluye la respuesta correcta."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    orden: int
    tipo: TipoPregunta
    enunciado: str
    opciones_json: list[str] | None


class PreguntaExamenResponse(BaseModel):
    """Pregunta de examen completa, tal como la ve RRHH — incluye respuesta correcta y calificación."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    examen_id: str
    orden: int
    tipo: TipoPregunta
    enunciado: str
    opciones_json: list[str] | None
    respuesta_correcta: str | None
    respuesta_candidato: str | None
    puntos_max: float
    puntos_obtenidos: float | None
    feedback_ia: str | None


class ExamenResponse(BaseModel):
    """Representación de un examen, sin el detalle de sus preguntas."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    candidato_id: str
    vacante_id: str
    estado: EstadoExamen
    nota: float | None
    duracion_minutos: int
    semaforo: SemaforoExamen
    puntaje_riesgo: int
    fecha_inicio: datetime | None
    fecha_fin: datetime | None
    created_at: datetime


class ExamenDetalleResponse(ExamenResponse):
    """Examen con el detalle completo de sus preguntas y respuestas."""

    preguntas: list[PreguntaExamenResponse]


class EventoAuditoriaResponse(BaseModel):
    """Evento de proctoring registrado durante un examen."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    examen_id: str
    tipo: str
    severidad: SeveridadEvento
    detalle: str | None
    timestamp: datetime


class CandidatoAccesoResponse(BaseModel):
    """Datos del candidato retornados al validar su token de acceso."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    vacante_id: str
    nombre: str
    apellidos: str
    email: str
    estado: EstadoCandidato


class IniciarExamenResponse(BaseModel):
    """Examen iniciado, con el pliego de preguntas para el candidato."""

    examen_id: str
    duracion_minutos: int
    preguntas: list[PreguntaExamenPublica]


class GuardarRespuestaRequest(BaseModel):
    """Respuesta del candidato a una pregunta del examen (auto-guardado)."""

    pregunta_id: str
    respuesta: str


class FinalizarExamenResponse(BaseModel):
    """Resultado de la calificación automática del examen."""

    nota: float | None
    semaforo: SemaforoExamen
    mensaje: str


class EventoProctoringRequest(BaseModel):
    """Evento de proctoring detectado durante el examen (catálogo en la sección 11 del CLAUDE.md)."""

    tipo: str = Field(min_length=1)
    detalle: str | None = None


class ProgresoCandidatoResponse(BaseModel):
    """Estado actual del candidato en su proceso de selección."""

    candidato_id: str
    estado: EstadoCandidato
    es_finalista: bool


class MensajeResponse(BaseModel):
    """Respuesta genérica de confirmación."""

    detail: str
