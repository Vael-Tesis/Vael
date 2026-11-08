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


def datos_prompt_vacante(vacante: Vacante, area: Area | None) -> dict[str, Any]:
    """Datos de la vacante y del área que necesita el prompt, como diccionario serializable.

    Viajan en el mensaje de SQS para que la Lambda no consulte la base de datos (DEC-018).
    """
    return {
        "titulo": vacante.titulo,
        "nivel_experiencia": vacante.nivel_experiencia.value if vacante.nivel_experiencia else None,
        "requisitos": vacante.requisitos,
        "requisitos_deseables": vacante.requisitos_deseables,
        "habilidades": list(vacante.habilidades or []),
        "tecnologias": list(vacante.tecnologias or []),
        "instruccion_area": area.instruccion_ia if area else None,
    }


def construir_prompt_analisis(texto_cv: str, datos: dict[str, Any]) -> str:
    """Arma el prompt de análisis: texto del CV + requisitos de la vacante + instrucción del área.

    Recibe los datos de `datos_prompt_vacante`. El texto resultante es el mismo que antes de
    HU-23, para que las mediciones del OE2 sigan siendo comparables.
    """
    instruccion_area = datos.get("instruccion_area") or "Sin instrucciones adicionales del área."
    requisitos = datos.get("requisitos") or "No se especificaron requisitos obligatorios."
    requisitos_deseables = datos.get("requisitos_deseables") or "No se especificaron requisitos deseables."
    habilidades = ", ".join(datos["habilidades"]) if datos.get("habilidades") else "No especificadas."
    tecnologias = ", ".join(datos["tecnologias"]) if datos.get("tecnologias") else "No especificadas."
    nivel = datos.get("nivel_experiencia") or "no especificado"

    return f"""
Eres un reclutador técnico experto evaluando el CV de un candidato para una vacante.

## Vacante: {datos["titulo"]}
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


def preparar_mensaje_analisis_cv(candidato: Candidato, vacante: Vacante, area: Area | None) -> dict[str, Any]:
    """Parte de preparación (backend): todo lo que el cálculo necesita, sin objetos de la base.

    Es el cuerpo del mensaje de SQS (DEC-016) y la entrada de `calcular_analisis_cv`.
    """
    if not candidato.cv_url:
        raise ValueError(f"El candidato {candidato.id} no tiene cv_url — no hay CV para analizar")
    return {
        "tipo": "analisis_cv",
        "tenant_id": candidato.tenant_id,
        "candidato_id": candidato.id,
        "cv_key": clave_desde_url(candidato.cv_url),
        "vacante": datos_prompt_vacante(vacante, area),
    }


async def calcular_analisis_cv(mensaje: dict[str, Any]) -> dict[str, Any]:
    """Parte de cálculo: Lambda en producción, en proceso en desarrollo. No toca la base (DEC-018).

    1. Descarga el PDF del bucket privado con el cliente de S3 (una URL sin firma da 403)
    2. Extrae su texto (PyPDF2, con fallback a pdfminer)
    3. Si no hay texto (PDF escaneado), no llama a la IA y devuelve `sin_texto`
    4. Arma el prompt y llama a Gemini
    5. Valida el desglose y suma `score_cv` (DEC-024); si no cumple, lanza ValueError

    Devuelve el resultado que se entrega al backend por /api/interno/resultados/analisis-cv.
    """
    base = {"tenant_id": mensaje["tenant_id"], "candidato_id": mensaje["candidato_id"]}

    pdf_bytes = await descargar_archivo(mensaje["cv_key"])
    texto_cv = extraer_texto_pdf(pdf_bytes)
    if not texto_cv.strip():
        # PDF escaneado o sin texto: no se envía a la IA; RRHH lo revisa a mano (doc 13, CV-TI-11)
        return {**base, "sin_texto": True}

    prompt = construir_prompt_analisis(texto_cv, mensaje["vacante"])
    respuesta = await consultar_gemini_json(prompt)

    # DEC-024: el sistema valida y suma; no se ajusta ningún valor en silencio
    score_cv, score_desglose = _validar_y_sumar_desglose(respuesta.get("criterios"))

    return {
        **base,
        "sin_texto": False,
        "score_cv": score_cv,
        "score_desglose": score_desglose,
        "clasificacion": _como_clasificacion(respuesta.get("clasificacion")).value,
        "resumen": respuesta.get("resumen"),
        "habilidades_detectadas": como_lista_str(respuesta.get("habilidades_detectadas")),
        "inconsistencias": como_lista_str(respuesta.get("inconsistencias")),
        "linkedin": respuesta.get("linkedin"),
        "github": respuesta.get("github"),
        "portfolio": respuesta.get("portfolio"),
    }


# Estados en los que un resultado de análisis todavía puede aplicarse. Si el candidato ya está
# en otro (el resultado ya se aplicó o RRHH ya decidió), una entrega repetida de SQS no cambia
# nada (DEC-016, punto 7: idempotencia).
ESTADOS_QUE_ACEPTAN_ANALISIS_CV = frozenset({EstadoCandidato.POSTULADO, EstadoCandidato.CV_ANALIZANDO})


async def aplicar_resultado_analisis_cv(candidato: Candidato, resultado: dict[str, Any], db: AsyncSession) -> bool:
    """Parte de aplicación (backend): guarda el análisis y deja al candidato en cv_por_confirmar.

    DEC-009: la IA recomienda; RRHH decide. La recomendación (score_cv frente a
    score_cv_minimo) la calcula el servicio de decisiones; aquí no se emiten tokens ni correos.
    Devuelve False si el resultado ya se había aplicado (idempotencia).
    """
    if candidato.estado not in ESTADOS_QUE_ACEPTAN_ANALISIS_CV:
        logger.info(
            "Resultado de análisis de CV ignorado: el candidato %s ya está en %s",
            candidato.id,
            candidato.estado,
            extra={"tenant_id": candidato.tenant_id, "candidato_id": candidato.id},
        )
        return False

    if resultado.get("sin_texto"):
        candidato.score_cv = None
        candidato.clasificacion_ia = ClasificacionIA.REQUIERE_REVISION
        candidato.resumen_ia = MENSAJE_CV_SIN_TEXTO
    else:
        candidato.score_cv = resultado["score_cv"]
        candidato.score_desglose = resultado["score_desglose"]
        candidato.clasificacion_ia = _como_clasificacion(resultado.get("clasificacion"))
        candidato.resumen_ia = resultado.get("resumen")
        candidato.habilidades_detectadas = como_lista_str(resultado.get("habilidades_detectadas"))
        candidato.inconsistencias = como_lista_str(resultado.get("inconsistencias"))
        candidato.linkedin = candidato.linkedin or resultado.get("linkedin")
        candidato.github = candidato.github or resultado.get("github")
        candidato.portfolio = candidato.portfolio or resultado.get("portfolio")

    candidato.analizado_en = utcnow()
    candidato.updated_at = utcnow()
    candidato.estado = EstadoCandidato.CV_POR_CONFIRMAR
    db.add(candidato)
    await db.commit()
    return True


async def analizar_cv(candidato: Candidato, vacante: Vacante, area: Area | None, db: AsyncSession) -> None:
    """Análisis completo en el mismo proceso: preparación, cálculo y aplicación (desarrollo y tests).

    En producción el cálculo corre en la Lambda y el resultado llega por el endpoint interno.
    """
    mensaje = preparar_mensaje_analisis_cv(candidato, vacante, area)
    resultado = await calcular_analisis_cv(mensaje)
    await aplicar_resultado_analisis_cv(candidato, resultado, db)


async def cargar_para_analisis_cv(candidato_id: str, db: AsyncSession) -> tuple[Candidato, Vacante, Area | None] | None:
    """Carga el candidato, su vacante y su área; None si alguno ya no existe."""
    candidato = await db.get(Candidato, candidato_id)
    if candidato is None:
        return None
    vacante = await db.get(Vacante, candidato.vacante_id)
    if vacante is None:
        return None
    area = await db.get(Area, vacante.area_id)
    return candidato, vacante, area


async def analizar_cv_candidato(candidato_id: str) -> None:
    """Punto de entrada del despachador en modo en proceso: abre su propia sesión de BD.

    Corre después de que la sesión del request original ya se cerró, por eso no la reutiliza.
    """
    async with async_session_factory() as db:
        cargado = await cargar_para_analisis_cv(candidato_id, db)
        if cargado is None:
            return
        candidato, vacante, area = cargado
        tenant_actual.set(candidato.tenant_id)

        try:
            with medir_operacion(logger, "analisis_cv", candidato_id=candidato_id):
                await analizar_cv(candidato, vacante, area, db)
        except Exception:
            logger.exception("Falló el análisis de CV del candidato %s", candidato_id)
            candidato.estado = EstadoCandidato.POSTULADO
            db.add(candidato)
            await db.commit()
