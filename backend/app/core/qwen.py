"""Cliente del modelo Qwen del instituto, respaldo de Gemini (DEC-025, propuesta; DEV-C-15).

El servidor de IA del instituto expone una API compatible con la de OpenAI
(`POST {QWEN_BASE_URL}/chat/completions`), el formato habitual de los despliegues locales de
Qwen (vLLM, Ollama, LM Studio). Solo se usa para las llamadas de texto con salida JSON
(`consultar_gemini_json`); la entrevista por voz con Gemini Live no tiene respaldo.

Los prompts de VAEL ya exigen "ÚNICAMENTE un JSON"; aun así, si el modelo envuelve la respuesta
en un bloque de markdown, se le quita antes de parsearla.
"""
import asyncio
import json
import logging
import re
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

CODIGOS_REINTENTABLES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
MAX_INTENTOS = 3
TIEMPO_LIMITE_SEGUNDOS = 90.0  # un modelo local puede tardar más que Gemini en respuestas largas
ESPERA_BASE_SEGUNDOS = 2.0
_BLOQUE_MARKDOWN = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)

INSTRUCCION_SISTEMA = "Responde únicamente con un objeto JSON válido, sin texto adicional ni bloques de markdown."


def qwen_configurado() -> bool:
    """True si hay URL y modelo de Qwen configurados."""
    return bool(settings.qwen_base_url and settings.qwen_model)


def _url(ruta: str) -> str:
    return settings.qwen_base_url.rstrip("/") + ruta


def _cabeceras() -> dict[str, str]:
    cabeceras = {"Content-Type": "application/json"}
    if settings.qwen_api_key:
        cabeceras["Authorization"] = f"Bearer {settings.qwen_api_key}"
    return cabeceras


def extraer_json(texto: str) -> dict[str, Any]:
    """Parsea la respuesta del modelo como JSON, quitando un bloque ```json ... ``` si lo hay."""
    coincidencia = _BLOQUE_MARKDOWN.match(texto or "")
    limpio = coincidencia.group(1) if coincidencia else (texto or "")
    try:
        valor = json.loads(limpio)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Qwen no devolvió un JSON válido: {texto!r}") from exc
    if not isinstance(valor, dict):
        raise ValueError(f"Qwen devolvió JSON que no es un objeto: {texto!r}")
    return valor


async def consultar_qwen_json(prompt: str) -> dict[str, Any]:
    """Llama al modelo Qwen del instituto pidiendo JSON y devuelve el dict parseado.

    Reintenta ante 429 y 5xx o sin respuesta en TIEMPO_LIMITE_SEGUNDOS, hasta MAX_INTENTOS veces.
    """
    if not qwen_configurado():
        raise RuntimeError("Qwen no está configurado: faltan QWEN_BASE_URL o QWEN_MODEL")

    cuerpo = {
        "model": settings.qwen_model,
        "messages": [
            {"role": "system", "content": INSTRUCCION_SISTEMA},
            {"role": "user", "content": prompt},
        ],
    }
    inicio = time.perf_counter()
    async with httpx.AsyncClient(timeout=TIEMPO_LIMITE_SEGUNDOS) as cliente:
        for intento in range(1, MAX_INTENTOS + 1):
            try:
                respuesta = await cliente.post(_url("/chat/completions"), json=cuerpo, headers=_cabeceras())
                if respuesta.status_code in CODIGOS_REINTENTABLES and intento < MAX_INTENTOS:
                    raise httpx.HTTPStatusError("reintentable", request=respuesta.request, response=respuesta)
                respuesta.raise_for_status()
                break
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                reintentable = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code in CODIGOS_REINTENTABLES
                if not reintentable or intento == MAX_INTENTOS:
                    raise
                espera = ESPERA_BASE_SEGUNDOS * 2 ** (intento - 1)
                logger.warning("Qwen falló (%r); reintento %d de %d en %.1f s", exc, intento, MAX_INTENTOS - 1, espera)
                await asyncio.sleep(espera)

    duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
    logger.info(
        "Llamada a Qwen: modelo=%s, intentos=%d, duracion_ms=%.1f",
        settings.qwen_model,
        intento,
        duracion_ms,
        extra={"operation": "qwen_chat_completions", "duration_ms": duracion_ms},
    )
    datos = respuesta.json()
    try:
        contenido = datos["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Respuesta de Qwen sin contenido: {datos!r}") from exc
    return extraer_json(contenido)


async def listar_modelos() -> list[str]:
    """IDs de los modelos que expone el servidor (`GET /models`). Sirve para descubrir el modelo."""
    async with httpx.AsyncClient(timeout=30.0) as cliente:
        respuesta = await cliente.get(_url("/models"), headers=_cabeceras())
    respuesta.raise_for_status()
    return [str(m.get("id")) for m in respuesta.json().get("data", []) if isinstance(m, dict)]
