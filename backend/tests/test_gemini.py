"""Pruebas del cliente de Gemini (DEV-C-04): JSON, reintento ante 429/503 y errores.

No llaman a la API real: se reemplaza el cliente por uno simulado.
"""
import logging
from types import SimpleNamespace
from typing import Any

import pytest
from google.genai import errors

from app.core import gemini


class _ModelosFalsos:
    """Imita client.aio.models: devuelve o lanza, en orden, lo que se le indique."""

    def __init__(self, respuestas: list[Any]) -> None:
        self._respuestas = list(respuestas)
        self.llamadas: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> Any:
        self.llamadas.append(kwargs)
        siguiente = self._respuestas.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return SimpleNamespace(text=siguiente)


@pytest.fixture
def cliente_falso(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Instala un cliente simulado y anula las esperas del backoff."""

    def instalar(respuestas: list[Any]) -> _ModelosFalsos:
        modelos = _ModelosFalsos(respuestas)
        monkeypatch.setattr(gemini, "_cliente", lambda: SimpleNamespace(aio=SimpleNamespace(models=modelos)))
        return modelos

    async def sin_espera(_segundos: float) -> None:
        return None

    monkeypatch.setattr(gemini.asyncio, "sleep", sin_espera)
    return instalar


def _error(codigo: int) -> errors.APIError:
    clase = errors.ClientError if codigo < 500 else errors.ServerError
    return clase(codigo, {"error": {"code": codigo, "message": "simulado", "status": "X"}})


async def test_devuelve_el_json_parseado(cliente_falso: Any) -> None:
    """Una respuesta JSON válida se devuelve como dict."""
    cliente_falso(['{"score": 78}'])
    assert await gemini.consultar_gemini_json("prompt") == {"score": 78}


async def test_usa_el_modelo_configurado_y_pide_json(cliente_falso: Any) -> None:
    """Sin model_name usa settings.gemini_model y pide response_mime_type JSON."""
    modelos = cliente_falso(['{"ok": true}'])
    await gemini.consultar_gemini_json("prompt")
    llamada = modelos.llamadas[0]
    assert llamada["model"] == gemini.settings.gemini_model
    assert llamada["config"].response_mime_type == "application/json"


@pytest.mark.parametrize("codigo", [429, 503])
async def test_reintenta_ante_429_y_503(cliente_falso: Any, codigo: int) -> None:
    """Ante cuota agotada o servicio saturado, reintenta y termina devolviendo el resultado."""
    modelos = cliente_falso([_error(codigo), _error(codigo), '{"ok": true}'])
    assert await gemini.consultar_gemini_json("prompt") == {"ok": True}
    assert len(modelos.llamadas) == 3


async def test_no_reintenta_errores_no_transitorios(cliente_falso: Any) -> None:
    """Un 400 (prompt inválido) se propaga de inmediato, sin reintentos."""
    modelos = cliente_falso([_error(400), '{"ok": true}'])
    with pytest.raises(errors.APIError):
        await gemini.consultar_gemini_json("prompt")
    assert len(modelos.llamadas) == 1


async def test_propaga_el_error_al_agotar_los_reintentos(cliente_falso: Any) -> None:
    """Tras MAX_INTENTOS fallos 429, el error se propaga (la tarea falla de forma visible)."""
    modelos = cliente_falso([_error(429)] * gemini.MAX_INTENTOS)
    with pytest.raises(errors.APIError):
        await gemini.consultar_gemini_json("prompt")
    assert len(modelos.llamadas) == gemini.MAX_INTENTOS


async def test_json_invalido_lanza_value_error(cliente_falso: Any) -> None:
    """Si Gemini no devuelve JSON, el error lo dice con el texto recibido."""
    cliente_falso(["esto no es json"])
    with pytest.raises(ValueError, match="no devolvió un JSON válido"):
        await gemini.consultar_gemini_json("prompt")


async def test_registra_modelo_e_intentos(cliente_falso: Any, caplog: pytest.LogCaptureFixture) -> None:
    """Cada llamada deja en el log el modelo exacto y cuántos intentos tomó (OE2)."""
    cliente_falso([_error(429), '{"ok": true}'])
    with caplog.at_level(logging.INFO, logger="app.core.gemini"):
        await gemini.consultar_gemini_json("prompt", model_name="modelo-de-prueba")
    mensaje = caplog.records[-1].getMessage()
    assert "modelo=modelo-de-prueba" in mensaje
    assert "intentos=2" in mensaje


def test_backoff_crece_exponencialmente() -> None:
    """Las esperas base son 2, 4 y 8 segundos, más un jitter menor a 1 segundo."""
    for intento, base in [(1, 2.0), (2, 4.0), (3, 8.0)]:
        assert base <= gemini._espera_backoff(intento) < base + 1


def test_el_modelo_por_defecto_no_es_el_id_inexistente() -> None:
    """gemini-3-flash no existe en la API (verificado en DEV-C-04)."""
    assert gemini.settings.gemini_model != "gemini-3-flash"
