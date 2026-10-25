"""Schemas de las decisiones humanas — /api/candidatos/ (DEC-009)."""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.decision import EtapaDecision, TipoDecision
from app.models.evaluacion import SemaforoExamen
from app.schemas.candidato import CandidatoResponse
from app.schemas.tag import TagResponse


def _a_utc_sin_zona(valor: datetime | None) -> datetime | None:
    """Las columnas son TIMESTAMP sin zona en UTC: una fecha con zona (p. ej. ...Z del navegador)
    se convierte a UTC y se le quita la zona."""
    if valor is not None and valor.tzinfo is not None:
        return valor.astimezone(timezone.utc).replace(tzinfo=None)
    return valor


class DecisionRequest(BaseModel):
    """Decisión individual de RRHH sobre la etapa pendiente de un candidato."""

    etapa: EtapaDecision
    decision: TipoDecision
    justificacion_humana: str | None = Field(
        default=None, description="Obligatoria si la decisión no coincide con la recomendación de la IA"
    )
    revision_inicio: datetime | None = Field(
        default=None, description="Momento en que RRHH abrió la recomendación (minutos de revisión, OE1)"
    )

    _revision_utc = field_validator("revision_inicio")(_a_utc_sin_zona)


class DecisionLoteItem(BaseModel):
    """Una decisión dentro de un lote."""

    candidato_id: str
    decision: TipoDecision


class DecisionLoteRequest(BaseModel):
    """Confirmación en lote de una etapa: solo decisiones que coinciden con la IA."""

    etapa: EtapaDecision
    decisiones: list[DecisionLoteItem] = Field(min_length=1)
    revision_inicio: datetime | None = None

    _revision_utc = field_validator("revision_inicio")(_a_utc_sin_zona)


class DecisionResponse(BaseModel):
    """Fila de decisiones_candidato."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    candidato_id: str
    etapa: EtapaDecision
    recomendacion_ia: TipoDecision | None
    puntaje: float | None
    umbral: float | None
    justificacion_ia: str | None
    decision: TipoDecision
    coincide_con_ia: bool | None
    justificacion_humana: str | None
    decidido_por: str
    decidido_por_nombre: str | None = None
    revision_inicio: datetime | None
    decidido_en: datetime
    reemplaza_a: str | None


class RecomendacionPendienteResponse(BaseModel):
    """Elemento de la bandeja: candidato a la espera de una decisión, con la recomendación de la IA."""

    candidato: CandidatoResponse
    etapa: EtapaDecision
    recomendacion_ia: TipoDecision | None
    puntaje: float | None
    umbral: float | None
    justificacion_ia: str | None
    semaforo: SemaforoExamen | None = Field(default=None, description="Semáforo de integridad del examen (etapa examen)")


class CandidatoDetalleResponse(CandidatoResponse):
    """Detalle del candidato con su historial de decisiones (HU-16) y sus etiquetas (HU-13)."""

    decisiones: list[DecisionResponse] = []
    tags: list[TagResponse] = []
