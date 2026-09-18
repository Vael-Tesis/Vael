"""Schemas de request y response para el portal público — /api/publico/."""
from datetime import datetime

from pydantic import BaseModel

from app.models.vacante import Modalidad, NivelExperiencia, TipoContrato


class VacantePublicaResponse(BaseModel):
    """Vista pública de una vacante — sin campos internos (umbrales de IA, tenant_id, etc.)."""

    codigo: str
    titulo: str
    empresa: str | None

    descripcion: str | None
    responsabilidades: str | None
    requisitos: str | None
    requisitos_deseables: str | None
    beneficios: str | None
    habilidades: list[str]
    tecnologias: list[str]

    nivel_experiencia: NivelExperiencia | None
    modalidad: Modalidad | None
    tipo_contrato: TipoContrato | None

    ciudad: str | None
    pais: str | None
    salario_minimo: float | None
    salario_maximo: float | None
    moneda: str | None

    cantidad_posiciones: int
    fecha_limite: datetime | None


class PostulacionResponse(BaseModel):
    """Confirmación de una postulación recibida."""

    candidato_id: str
    mensaje: str
