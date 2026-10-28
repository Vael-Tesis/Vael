"""Cliente compartido de Google Gemini: llamada con salida JSON, reintentos y registro (DEV-C-04).

Centraliza lo que repiten services/analisis_cv.py, services/examen.py, services/entrevista_ia.py
y services/vacante_ia.py: cada uno arma su prompt, pero todos llaman a Gemini y parsean JSON
de la misma forma. Usa el SDK `google-genai`, el único de Gemini en el proyecto.

- Reintento con backoff exponencial y jitter ante 429 (cuota), 503 (servicio saturado), 504
  (plazo vencido en Google) y llamadas sin respuesta en TIEMPO_LIMITE_SEGUNDOS.
- Cada llamada registra el modelo exacto, los parámetros, los intentos y la duración: el OE2
  exige saber con qué modelo y configuración se obtuvo cada puntaje (plan de métricas).
"""
import asyncio
import json
import logging
import random
import time
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import errors, types

from app.core.config import settings

logger = logging.getLogger(__name__)

CODIGOS_REINTENTABLES: frozenset[int] = frozenset({429, 503, 504})
MAX_INTENTOS = 4
# Una llamada colgada dejaba al candidato en "analizando" varios minutos (observación de TST-A-01)
TIEMPO_LIMITE_SEGUNDOS = 60.0
ESPERA_BASE_SEGUNDOS = 2.0


@lru_cache
def _cliente() -> genai.Client:
    """Cliente de Gemini reutilizado entre llamadas (se crea al primer uso)."""
    return genai.Client(api_key=settings.gemini_api_key)


def _configuracion_json() -> types.GenerateContentConfig:
    """Pide respuesta JSON y desactiva la llamada automática a funciones (VAEL no la usa)."""
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def _espera_backoff(intento: int) -> float:
    """Segundos a esperar antes del siguiente intento: 2, 4, 8... más hasta 1 s de jitter."""
    return ESPERA_BASE_SEGUNDOS * 2 ** (intento - 1) + random.uniform(0, 1)


async def consultar_gemini_json(prompt: str, model_name: str | None = None) -> dict[str, Any]:
    """Llama a un modelo Gemini pidiendo salida JSON y parsea la respuesta como dict.

    Reintenta ante 429, 503, 504 o sin respuesta en TIEMPO_LIMITE_SEGUNDOS, hasta MAX_INTENTOS
    veces; cualquier otro error se propaga de inmediato. Si se agotan los reintentos, propaga
    el último error para que la tarea falle de forma visible (en AWS, el mensaje vuelve a la
    cola y termina en la DLQ).
    """
    modelo = model_name or settings.gemini_model
    configuracion = _configuracion_json()
    inicio = time.perf_counter()

    for intento in range(1, MAX_INTENTOS + 1):
        try:
            respuesta = await asyncio.wait_for(
                _cliente().aio.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=configuracion,
                ),
                TIEMPO_LIMITE_SEGUNDOS,
            )
            break
        except (errors.APIError, TimeoutError) as exc:
            sin_respuesta = isinstance(exc, TimeoutError)
            if (not sin_respuesta and exc.code not in CODIGOS_REINTENTABLES) or intento == MAX_INTENTOS:
                raise
            espera = _espera_backoff(intento)
            logger.warning(
                "Gemini respondió %s con el modelo %s; reintento %d de %d en %.1f s",
                f"sin respuesta en {TIEMPO_LIMITE_SEGUNDOS:.0f} s" if sin_respuesta else exc.code,
                modelo,
                intento,
                MAX_INTENTOS - 1,
                espera,
            )
            await asyncio.sleep(espera)

    duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
    logger.info(
        "Llamada a Gemini: modelo=%s, response_mime_type=application/json, intentos=%d, duracion_ms=%.1f",
        modelo,
        intento,
        duracion_ms,
        extra={"operation": "gemini_generate_content", "duration_ms": duracion_ms},
    )

    try:
        return json.loads(respuesta.text)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError(f"Gemini no devolvió un JSON válido: {getattr(respuesta, 'text', respuesta)!r}") from exc


def como_lista_str(valor: Any) -> list[str]:
    """Normaliza un valor de una respuesta JSON de Gemini a list[str], descartando lo que no lo sea."""
    if not isinstance(valor, list):
        return []
    return [str(item) for item in valor if isinstance(item, str)]
