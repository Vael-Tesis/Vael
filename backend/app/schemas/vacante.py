"""Schemas de request y response para vacantes — /api/vacantes/."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.vacante import EstadoVacante, Modalidad, NivelExperiencia, PrioridadVacante, TipoContrato


class VacanteCreateRequest(BaseModel):
    """Datos para crear una vacante (wizard de 4 pasos) — el código se genera automáticamente."""

    area_id: str
    titulo: str = Field(min_length=1)

    descripcion: str | None = None
    responsabilidades: str | None = None
    requisitos: str | None = None
    requisitos_deseables: str | None = None
    beneficios: str | None = None
    habilidades: list[str] = Field(default_factory=list)
    tecnologias: list[str] = Field(default_factory=list)

    nivel_experiencia: NivelExperiencia | None = None
    anios_experiencia: int | None = None
    modalidad: Modalidad | None = None
    tipo_contrato: TipoContrato | None = None

    ciudad: str | None = None
    pais: str | None = None
    salario_minimo: float | None = None
    salario_maximo: float | None = None
    moneda: str | None = "PEN"
    mostrar_salario: bool = False

    confidencial: bool = False
    prioridad: PrioridadVacante = PrioridadVacante.MEDIA
    fecha_limite: datetime | None = None

    jefe_directo: str | None = None
    solicitante: str | None = None
    cantidad_posiciones: int = 1

    score_cv_minimo: int = 60
    nota_minima_examen: int = 13
    top_candidatos_finalistas: int = 5
    instruccion_ia_extra: str | None = None


class VacanteUpdateRequest(BaseModel):
    """Datos editables de una vacante — todos opcionales (actualización parcial).

    area_id y codigo no son editables aquí: el código depende del área con la que
    se generó y cambiarla lo dejaría inconsistente.
    """

    titulo: str | None = None
    descripcion: str | None = None
    responsabilidades: str | None = None
    requisitos: str | None = None
    requisitos_deseables: str | None = None
    beneficios: str | None = None
    habilidades: list[str] | None = None
    tecnologias: list[str] | None = None

    nivel_experiencia: NivelExperiencia | None = None
    anios_experiencia: int | None = None
    modalidad: Modalidad | None = None
    tipo_contrato: TipoContrato | None = None

    ciudad: str | None = None
    pais: str | None = None
    salario_minimo: float | None = None
    salario_maximo: float | None = None
    moneda: str | None = None
    mostrar_salario: bool | None = None

    confidencial: bool | None = None
    prioridad: PrioridadVacante | None = None
    fecha_limite: datetime | None = None

    jefe_directo: str | None = None
    solicitante: str | None = None
    cantidad_posiciones: int | None = None

    score_cv_minimo: int | None = None
    nota_minima_examen: int | None = None
    top_candidatos_finalistas: int | None = None
    instruccion_ia_extra: str | None = None


class VacanteResponse(BaseModel):
    """Representación completa de una vacante."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    area_id: str
    codigo: str
    titulo: str

    descripcion: str | None
    responsabilidades: str | None
    requisitos: str | None
    requisitos_deseables: str | None
    beneficios: str | None
    habilidades: list[str]
    tecnologias: list[str]

    nivel_experiencia: NivelExperiencia | None
    anios_experiencia: int | None
    modalidad: Modalidad | None
    tipo_contrato: TipoContrato | None

    ciudad: str | None
    pais: str | None
    salario_minimo: float | None
    salario_maximo: float | None
    moneda: str | None
    mostrar_salario: bool

    confidencial: bool
    estado: EstadoVacante
    prioridad: PrioridadVacante
    fecha_limite: datetime | None

    jefe_directo: str | None
    solicitante: str | None
    cantidad_posiciones: int

    score_cv_minimo: int
    nota_minima_examen: int
    top_candidatos_finalistas: int
    instruccion_ia_extra: str | None

    created_at: datetime
    updated_at: datetime


class TextosMarketingResponse(BaseModel):
    """Textos de difusión generados por IA para distintos canales (LinkedIn, WhatsApp, etc.)."""

    textos: dict[str, str]
