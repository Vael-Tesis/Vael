"""Servicio de análisis de CV con Google Gemini."""
import logging
from io import BytesIO
from typing import Any

from pdfminer.high_level import extract_text as pdfminer_extract_text
from PyPDF2 import PdfReader
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import async_session_factory
from app.core.gemini import como_lista_str, consultar_gemini_json
from app.core.logs import medir_operacion, tenant_actual
from app.models.area import Area
from app.models.base import utcnow
from app.models.candidato import Candidato, ClasificacionIA, EstadoCandidato
from app.models.vacante import Vacante
from app.services.aws_services import clave_desde_url, descargar_archivo

logger = logging.getLogger(__name__)

MENSAJE_CV_SIN_TEXTO = (
    "No se pudo extraer texto del CV (posible documento escaneado). No se analizó con IA: requiere revisión manual."
)

# DEC-024: desglose ponderado y auditable de score_cv. Los pesos son fijos para todo el
# sistema en esta versión (DEC-024, punto 6).
PESO_MAXIMO_MATCH_HABILIDADES = 40
PESO_MAXIMO_EXPERIENCIA = 20
PESO_MAXIMO_FORMACION = 15
PESO_MAXIMO_COHERENCIA = 15
PESO_MAXIMO_TRAYECTORIA = 10

CRITERIOS_SCORE_CV: dict[str, int] = {
    "match_habilidades": PESO_MAXIMO_MATCH_HABILIDADES,
    "experiencia": PESO_MAXIMO_EXPERIENCIA,
    "formacion": PESO_MAXIMO_FORMACION,
    "coherencia": PESO_MAXIMO_COHERENCIA,
    "trayectoria": PESO_MAXIMO_TRAYECTORIA,
}


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
Evalúa qué tan bien encaja este candidato con la vacante, puntuando cada uno de los
siguientes cinco criterios por separado (no calcules el total: lo calcula el sistema).
Responde ÚNICAMENTE con un JSON (sin texto adicional, sin bloques de markdown) con
exactamente esta forma:

{{
  "criterios": {{
    "match_habilidades": {{"puntaje": <entero 0-{PESO_MAXIMO_MATCH_HABILIDADES}>, "justificacion": "<breve>"}},
    "experiencia": {{"puntaje": <entero 0-{PESO_MAXIMO_EXPERIENCIA}>, "justificacion": "<breve>"}},
    "formacion": {{"puntaje": <entero 0-{PESO_MAXIMO_FORMACION}>, "justificacion": "<breve>"}},
    "coherencia": {{"puntaje": <entero 0-{PESO_MAXIMO_COHERENCIA}>, "justificacion": "<breve>"}},
    "trayectoria": {{"puntaje": <entero 0-{PESO_MAXIMO_TRAYECTORIA}>, "justificacion": "<breve>"}}
  }},
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
    """Descarga el PDF del CV con el cliente de S3: el bucket es privado (doc 03), una URL sin firma da 403."""
    return await descargar_archivo(clave_desde_url(cv_url))


def _validar_y_sumar_desglose(criterios: Any) -> tuple[int, dict[str, dict[str, Any]]]:
    """Valida el desglose de criterios de Gemini y calcula score_cv como su suma (DEC-024).

    Verifica que estén los cinco criterios, que cada puntaje sea un entero dentro de su rango
    (0 a su peso máximo). Si algo no cumple, lanza ValueError: el análisis se trata como
    fallido por el camino de error que ya existe (analizar_cv_candidato); no se ajusta ningún
    valor en silencio (DEC-024, punto 3).
    """
    if not isinstance(criterios, dict):
        raise ValueError(f"Gemini no devolvió 'criterios' como un objeto: {criterios!r}")

    desglose: dict[str, dict[str, Any]] = {}
    score_total = 0

    for nombre, maximo in CRITERIOS_SCORE_CV.items():
        item = criterios.get(nombre)
        if not isinstance(item, dict):
            raise ValueError(f"Falta el criterio '{nombre}' en la respuesta de Gemini: {criterios!r}")

        puntaje = item.get("puntaje")
        if not isinstance(puntaje, int) or isinstance(puntaje, bool):
            raise ValueError(f"El criterio '{nombre}' no tiene un puntaje entero: {puntaje!r}")
        if not (0 <= puntaje <= maximo):
            raise ValueError(f"El criterio '{nombre}' está fuera de rango (0-{maximo}): {puntaje!r}")

        desglose[nombre] = {"puntaje": puntaje, "justificacion": str(item.get("justificacion") or "")}
        score_total += puntaje

    return score_total, desglose


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
    7. Deja al candidato en cv_por_confirmar: avanzar o descartar lo decide RRHH (DEC-009)
    """
    if not candidato.cv_url:
        raise ValueError(f"El candidato {candidato.id} no tiene cv_url — no hay CV para analizar")

    pdf_bytes = await _descargar_pdf(candidato.cv_url)
    texto_cv = extraer_texto_pdf(pdf_bytes)
    if not texto_cv.strip():
        # PDF escaneado o sin texto: no se envía a la IA; RRHH lo revisa a mano (doc 13, CV-TI-11)
        candidato.score_cv = None
        candidato.clasificacion_ia = ClasificacionIA.REQUIERE_REVISION
        candidato.resumen_ia = MENSAJE_CV_SIN_TEXTO
        candidato.analizado_en = utcnow()
        candidato.updated_at = utcnow()
        candidato.estado = EstadoCandidato.CV_POR_CONFIRMAR
        db.add(candidato)
        await db.commit()
        return

    prompt = construir_prompt_analisis(texto_cv, vacante, area)
    resultado = await consultar_gemini_json(prompt)

    # DEC-024: el backend valida y suma; si no cumple, se propaga y el candidato vuelve a
    # `postulado` por el camino de error existente (analizar_cv_candidato), sin guardar nada.
    score_cv, score_desglose = _validar_y_sumar_desglose(resultado.get("criterios"))

    candidato.score_cv = score_cv
    candidato.score_desglose = score_desglose
    candidato.clasificacion_ia = _como_clasificacion(resultado.get("clasificacion"))
    candidato.resumen_ia = resultado.get("resumen")
    candidato.habilidades_detectadas = como_lista_str(resultado.get("habilidades_detectadas"))
    candidato.inconsistencias = como_lista_str(resultado.get("inconsistencias"))
    candidato.linkedin = candidato.linkedin or resultado.get("linkedin")
    candidato.github = candidato.github or resultado.get("github")
    candidato.portfolio = candidato.portfolio or resultado.get("portfolio")
    candidato.analizado_en = utcnow()
    candidato.updated_at = utcnow()

    # DEC-009: la IA recomienda; RRHH decide. La recomendación (score_cv frente a
    # score_cv_minimo) la calcula el servicio de decisiones; aquí no se emiten tokens ni correos.
    candidato.estado = EstadoCandidato.CV_POR_CONFIRMAR
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
        tenant_actual.set(candidato.tenant_id)

        try:
            with medir_operacion(logger, "analisis_cv", candidato_id=candidato_id):
                await analizar_cv(candidato, vacante, area, db)
        except Exception:
            logger.exception("Falló el análisis de CV del candidato %s", candidato_id)
            candidato.estado = EstadoCandidato.POSTULADO
            db.add(candidato)
            await db.commit()
