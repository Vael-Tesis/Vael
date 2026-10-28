"""Modelo: DecisionCandidato — registro de las decisiones humanas de avance y descarte (DEC-009)."""
from datetime import datetime
from enum import Enum

from sqlmodel import Field

from app.models.base import TenantBase, new_id, utcnow


class EtapaDecision(str, Enum):
    """Punto del proceso en el que RRHH decide."""

    CV = "cv"
    EXAMEN = "examen"
    ENTREVISTA = "entrevista"


class TipoDecision(str, Enum):
    """Sentido de una recomendación de la IA o de una decisión humana."""

    AVANZAR = "avanzar"
    DESCARTAR = "descartar"


class DecisionCandidato(TenantBase, table=True):
    """Decisión humana sobre un candidato en una etapa. Solo inserción: ninguna fila se edita
    ni se borra; revertir es insertar una fila nueva que apunta a la anterior con `reemplaza_a`.
    """

    __tablename__ = "decisiones_candidato"

    id: str = Field(default_factory=new_id, primary_key=True)
    candidato_id: str = Field(nullable=False, index=True, foreign_key="candidatos.id")
    etapa: EtapaDecision = Field(nullable=False)

    recomendacion_ia: TipoDecision | None = Field(default=None)
    puntaje: float | None = Field(default=None)
    umbral: float | None = Field(default=None)
    justificacion_ia: str | None = Field(default=None)

    decision: TipoDecision = Field(nullable=False)
    coincide_con_ia: bool | None = Field(default=None)
    justificacion_humana: str | None = Field(default=None)

    decidido_por: str = Field(nullable=False, foreign_key="usuarios.id")
    revision_inicio: datetime | None = Field(default=None)
    decidido_en: datetime = Field(default_factory=utcnow, nullable=False)
    reemplaza_a: str | None = Field(default=None, foreign_key="decisiones_candidato.id")
