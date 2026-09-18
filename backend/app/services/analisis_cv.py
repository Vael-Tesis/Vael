"""Servicio de análisis de CV con Google Gemini."""
import logging
from io import BytesIO
from typing import Any

import httpx
from pdfminer.high_level import extract_text as pdfminer_extract_text
from PyPDF2 import PdfReader
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import async_session_factory
from app.core.gemini import como_lista_str, consultar_gemini_json
from app.core.security import emitir_token_candidato
from app.models.area import Area
from app.models.base import utcnow
from app.models.candidato import Candidato, ClasificacionIA, EstadoCandidato
from app.models.usuario import TipoToken
from app.models.vacante import Vacante
from app.services.correos import correo_bienvenida_examen

logger = logging.getLogger(__name__)


def _extraer_con_pypdf2(pdf_bytes: bytes) -> str:
    """Extrae el texto de un PDF usando PyPDF2 (motor primario)."""
    try:
        lector = PdfReader(BytesIO(pdf_bytes))
        return "\n".join(pagina.extract_text() or "" for pagina in lector.pages)
    except Exception:
        logger.warning("PyPDF2 no pudo extraer el texto del CV, se intentará con pdfminer", exc_info=True)
        return ""


def _extraer_con_pdfminer(pdf_bytes: bytes) -> str:
    """Extrae el texto de un PDF usando pdfminer.six (fallback de PyPDF2)."""
    try:
        return pdfminer_extract_text(BytesIO(pdf_bytes))
    except Exception:
        logger.exception("pdfminer tampoco pudo extraer el texto del CV")
        return ""


def extraer_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrae el texto de un CV en PDF: intenta con PyPDF2 y, si no obtiene nada, usa pdfminer."""
    texto = _extraer_con_pypdf2(pdf_bytes)
    if texto.strip():
        return texto

    return _extraer_con_pdfminer(pdf_bytes)


def construir_prompt_analisis(texto_cv: str, vacante: Vacante, area: Area | None) -> str:
    """Arma el prompt de análisis: texto del CV + requisitos de la vacante + instrucción del área."""
    instruccion_area = (
        area.instruccion_ia if area and area.instruccion_ia else "Sin instrucciones adicionales del área."
    )
    requisitos = vacante.requisitos or "No se especificaron requisitos obligatorios."
    requisitos_deseables = vacante.requisitos_deseables or "No se especificaron requisitos deseables."
    habilidades = ", ".join(vacante.habilidades) if vacante.habilidades else "No especificadas."
    tecnologias = ", ".join(vacante.tecnologias) if vacante.tecnologias else "No especificadas."
    nivel = vacante.nivel_experiencia.value if vacante.nivel_experiencia else "no especificado"

    return f"""
Eres un reclutador técnico experto evaluando el CV de un candidato para una vacante.

## Vacante: {vacante.titulo}
Nivel de experiencia buscado: {nivel}
Requisitos obligatorios: {requisitos}
Requisitos deseables: {requisitos_deseables}
Habilidades buscadas: {habilidades}
Tecnologías buscadas: {tecnologias}

## Instrucción específica del área
{instruccion_area}

## Currículum del candidato (texto extraído del PDF)
{texto_cv}

## Tarea
Evalúa qué tan bien encaja este candidato con la vacante. Responde ÚNICAMENTE con un JSON
(sin texto adicional, sin bloques de markdown) con exactamente esta forma:

{{
  "score": <entero 0-100>,
  "clasificacion": "<altamente_recomendado|recomendado|requiere_revision|no_apto>",
  "resumen": "<3 a 4 oraciones resumiendo el encaje del candidato con la vacante>",
  "habilidades_detectadas": ["<habilidad1>", "<habilidad2>"],
  "inconsistencias": ["<inconsistencia1>"],
  "linkedin": "<url de LinkedIn si aparece en el CV, o null>",
  "github": "<url de GitHub si aparece en el CV, o null>",
  "portfolio": "<url de portafolio si aparece en el CV, o null>"
}}
""".strip()


async def _descargar_pdf(cv_url: str) -> bytes:
    """Descarga el PDF del CV desde su URL (S3/CloudFront)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        respuesta = await client.get(cv_url)
        respuesta.raise_for_status()
        return respuesta.content


def _como_score(valor: Any) -> int:
    """Normaliza el score de Gemini a un entero entre 0 y 100."""
    try:
        return max(0, min(100, int(valor)))
    except (TypeError, ValueError):
        return 0


def _como_clasificacion(valor: Any) -> ClasificacionIA:
    """Normaliza la clasificación de Gemini; si viene un valor inesperado, cae a requiere_revision."""
    try:
        return ClasificacionIA(valor)
    except ValueError:
        logger.warning("Gemini devolvió una clasificación fuera de catálogo: %r", valor)
        return ClasificacionIA.REQUIERE_REVISION


async def analizar_cv(candidato: Candidato, vacante: Vacante, area: Area | None, db: AsyncSession) -> None:
    """Analiza el CV de un candidato con Gemini y actualiza su registro (sección 10 del CLAUDE.md).

    1. Descarga el PDF desde cv_url
    2. Extrae su texto (PyPDF2, con fallback a pdfminer)
    3. Arma el prompt con el texto + los requisitos de la vacante + la instrucción del área
    4. Llama a Gemini 3 Flash
    5. Parsea la respuesta JSON
    6. Actualiza el candidato en BD
    7. Si score >= score_cv_minimo de la vacante: genera el token de examen y envía el correo
    8. Si score < score_cv_minimo: pasa a cv_rechazado, sin correo
    """
    if not candidato.cv_url:
        raise ValueError(f"El candidato {candidato.id} no tiene cv_url — no hay CV para analizar")

    pdf_bytes = await _descargar_pdf(candidato.cv_url)
    texto_cv = extraer_texto_pdf(pdf_bytes)
    prompt = construir_prompt_analisis(texto_cv, vacante, area)
    resultado = await consultar_gemini_json(prompt)

    candidato.score_cv = _como_score(resultado.get("score"))
    candidato.clasificacion_ia = _como_clasificacion(resultado.get("clasificacion"))
    candidato.resumen_ia = resultado.get("resumen")
    candidato.habilidades_detectadas = como_lista_str(resultado.get("habilidades_detectadas"))
    candidato.inconsistencias = como_lista_str(resultado.get("inconsistencias"))
    candidato.linkedin = candidato.linkedin or resultado.get("linkedin")
    candidato.github = candidato.github or resultado.get("github")
    candidato.portfolio = candidato.portfolio or resultado.get("portfolio")
    candidato.analizado_en = utcnow()
    candidato.updated_at = utcnow()

    if candidato.score_cv >= vacante.score_cv_minimo:
        candidato.estado = EstadoCandidato.CV_APROBADO
        db.add(candidato)
        await db.commit()
        await db.refresh(candidato)

        token = await emitir_token_candidato(candidato.id, candidato.tenant_id, TipoToken.EXAMEN, db)
        await correo_bienvenida_examen(candidato, token)
    else:
        candidato.estado = EstadoCandidato.CV_RECHAZADO
        db.add(candidato)
        await db.commit()


async def analizar_cv_candidato(candidato_id: str) -> None:
    """Punto de entrada para background tasks: abre su propia sesión de BD y ejecuta analizar_cv.

    Corre después de que la sesión del request original ya se cerró, por eso no la reutiliza.
    """
    async with async_session_factory() as db:
        candidato = await db.get(Candidato, candidato_id)
        if candidato is None:
            return

        vacante = await db.get(Vacante, candidato.vacante_id)
        if vacante is None:
            return

        area = await db.get(Area, vacante.area_id)

        try:
            await analizar_cv(candidato, vacante, area, db)
        except Exception:
            logger.exception("Falló el análisis de CV del candidato %s", candidato_id)
            candidato.estado = EstadoCandidato.POSTULADO
            db.add(candidato)
            await db.commit()
