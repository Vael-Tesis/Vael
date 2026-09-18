"""Cliente compartido de Google Gemini: configuración del SDK y llamada con salida JSON.

Centraliza lo que repiten services/analisis_cv.py, services/examen.py y
services/entrevista_ia.py — cada uno arma su propio prompt, pero todos necesitan
configurar el SDK con la API key y parsear una respuesta JSON de la misma forma.
"""
import json
from typing import Any

import google.generativeai as genai

from app.core.config import settings


async def consultar_gemini_json(prompt: str, model_name: str | None = None) -> dict[str, Any]:
    """Llama a un modelo Gemini pidiendo salida JSON y parsea la respuesta como dict."""
    genai.configure(api_key=settings.gemini_api_key)
    modelo = genai.GenerativeModel(model_name or settings.gemini_model)

    respuesta = await modelo.generate_content_async(
        prompt,
        generation_config=genai.GenerationConfig(response_mime_type="application/json"),
    )

    try:
        return json.loads(respuesta.text)
    except (json.JSONDecodeError, ValueError, AttributeError) as exc:
        raise ValueError(f"Gemini no devolvió un JSON válido: {getattr(respuesta, 'text', respuesta)!r}") from exc


def como_lista_str(valor: Any) -> list[str]:
    """Normaliza un valor de una respuesta JSON de Gemini a list[str], descartando lo que no lo sea."""
    if not isinstance(valor, list):
        return []
    return [str(item) for item in valor if isinstance(item, str)]
