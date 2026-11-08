"""Cuerpos de las entregas internas de las Lambdas (DEC-018, HU-23). No forman parte del OpenAPI."""
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.services.analisis_cv import CRITERIOS_SCORE_CV


class ResultadoAnalisisCv(BaseModel):
    """Resultado de `calcular_analisis_cv`."""

    tenant_id: str = Field(min_length=1)
    candidato_id: str = Field(min_length=1)
    sin_texto: bool = False
    score_cv: int | None = Field(default=None, ge=0, le=sum(CRITERIOS_SCORE_CV.values()))
    score_desglose: dict[str, dict[str, Any]] | None = None
    clasificacion: str | None = None
    resumen: str | None = None
    habilidades_detectadas: list[str] = []
    inconsistencias: list[str] = []
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None

    @model_validator(mode="after")
    def _con_puntaje_si_hubo_texto(self) -> "ResultadoAnalisisCv":
        """Un CV con texto analizado debe traer su puntaje y su desglose (DEC-024)."""
        if not self.sin_texto and (self.score_cv is None or self.score_desglose is None):
            raise ValueError("Un análisis con texto requiere score_cv y score_desglose")
        return self


class ResultadoAnalisisEntrevista(BaseModel):
    """Resultado de `calcular_analisis_entrevista`."""

    tenant_id: str = Field(min_length=1)
    entrevista_id: str = Field(min_length=1)
    dimensiones_json: dict[str, Any]
    nota: float = Field(ge=0, le=20)


class AplicacionResponse(BaseModel):
    """Indica si la entrega cambió algo; false si ya estaba aplicada o el registro no existe."""

    aplicado: bool
