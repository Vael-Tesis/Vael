"""Modelos: Examen, PreguntaExamen, EventoAuditoria."""
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TenantBase, new_id, utcnow


class EstadoExamen(str, Enum):
    """Estado del examen técnico de un candidato."""

    GENERANDO = "generando"
    PENDIENTE = "pendiente"
    EN_CURSO = "en_curso"
    FINALIZADO = "finalizado"
    EXPIRADO = "expirado"


class SemaforoExamen(str, Enum):
    """Nivel de riesgo de proctoring acumulado durante el examen (ver sección 11)."""

    VERDE = "verde"
    AMARILLO = "amarillo"
    ROJO = "rojo"


class TipoPregunta(str, Enum):
    """Tipo de pregunta del examen técnico."""

    MULTIPLE_CHOICE = "multiple_choice"
    ABIERTA = "abierta"


class SeveridadEvento(str, Enum):
    """Severidad de un evento de proctoring."""

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class Examen(TenantBase, table=True):
    """Examen técnico generado y calificado por IA para un candidato."""

    __tablename__ = "examenes"

    id: str = Field(default_factory=new_id, primary_key=True)
    candidato_id: str = Field(nullable=False, index=True, foreign_key="candidatos.id")
    vacante_id: str = Field(nullable=False, index=True, foreign_key="vacantes.id")

    estado: EstadoExamen = Field(default=EstadoExamen.GENERANDO, nullable=False, index=True)
    nota: float | None = Field(default=None)
    duracion_minutos: int = Field(default=45, nullable=False)

    semaforo: SemaforoExamen = Field(default=SemaforoExamen.VERDE, nullable=False)
    puntaje_riesgo: int = Field(default=0, nullable=False)

    fecha_inicio: datetime | None = Field(default=None)
    fecha_fin: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class PreguntaExamen(TenantBase, table=True):
    """Pregunta individual de un examen técnico (opción múltiple o abierta)."""

    __tablename__ = "preguntas_examen"

    id: str = Field(default_factory=new_id, primary_key=True)
    examen_id: str = Field(nullable=False, index=True, foreign_key="examenes.id")
    orden: int = Field(nullable=False)
    tipo: TipoPregunta = Field(nullable=False)

    enunciado: str = Field(nullable=False)
    opciones_json: list[str] | None = Field(default=None, sa_column=Column(JSON))
    respuesta_correcta: str | None = Field(default=None)
    respuesta_candidato: str | None = Field(default=None)

    puntos_max: float = Field(default=2.0, nullable=False)
    puntos_obtenidos: float | None = Field(default=None)
    feedback_ia: str | None = Field(default=None)


class EventoAuditoria(TenantBase, table=True):
    """Evento de proctoring registrado durante un examen o una entrevista (catálogo en sección 11).

    Pertenece a un examen (examen_id) o a una entrevista (entrevista_id) — exactamente uno
    de los dos debe venir informado, según en qué etapa se originó el evento.
    """

    __tablename__ = "eventos_auditoria"

    id: str = Field(default_factory=new_id, primary_key=True)
    examen_id: str | None = Field(default=None, index=True, foreign_key="examenes.id")
    entrevista_id: str | None = Field(default=None, index=True, foreign_key="entrevistas_ia.id")
    tipo: str = Field(nullable=False, max_length=50)
    severidad: SeveridadEvento = Field(nullable=False)
    detalle: str | None = Field(default=None)
    timestamp: datetime = Field(default_factory=utcnow, nullable=False)
