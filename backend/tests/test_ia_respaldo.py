"""IA de respaldo: Qwen del instituto cuando Gemini no está disponible (DEC-025, DEV-C-15)."""
import json
from typing import Any

import httpx
import pytest
from google.genai import errors

from app.core import gemini, qwen
from app.core.config import Settings, settings


def _servidor_qwen(contenido: str, vistas: list[httpx.Request] | None = None, estado: int = 200) -> Any:
    def responder(peticion: httpx.Request) -> httpx.Response:
        if vistas is not None:
            vistas.append(peticion)
        return httpx.Response(estado, json={"choices": [{"message": {"content": contenido}}]})

    cliente_real = httpx.AsyncClient
    return lambda **kw: cliente_real(transport=httpx.MockTransport(responder), **kw)


@pytest.fixture
def qwen_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "qwen_base_url", "https://ia.instituto.test/v1")
    monkeypatch.setattr(settings, "qwen_model", "qwen-prueba")
    monkeypatch.setattr(settings, "qwen_api_key", "clave-de-prueba")


def _gemini_que_falla(codigo: int) -> Any:
    async def falla(_prompt: str, _modelo: str | None = None) -> dict[str, Any]:
        raise errors.APIError(codigo, {"error": {"message": "falla simulada", "status": "X"}})

    return falla


async def test_si_gemini_no_esta_disponible_responde_qwen(monkeypatch: pytest.MonkeyPatch, qwen_configurado: None) -> None:
    vistas: list[httpx.Request] = []
    monkeypatch.setattr(settings, "ia_respaldo", "qwen")
    monkeypatch.setattr(gemini, "_consultar_gemini", _gemini_que_falla(429))
    monkeypatch.setattr(qwen.httpx, "AsyncClient", _servidor_qwen('{"score": 80}', vistas))

    assert await gemini.consultar_gemini_json("prompt") == {"score": 80}
    cuerpo = json.loads(vistas[0].content)
    assert str(vistas[0].url) == "https://ia.instituto.test/v1/chat/completions"
    assert cuerpo["model"] == "qwen-prueba"
    assert cuerpo["messages"][-1]["content"] == "prompt"
    assert vistas[0].headers["Authorization"] == "Bearer clave-de-prueba"


async def test_sin_respaldo_configurado_el_error_de_gemini_se_propaga(monkeypatch: pytest.MonkeyPatch, qwen_configurado: None) -> None:
    monkeypatch.setattr(settings, "ia_respaldo", "")
    monkeypatch.setattr(gemini, "_consultar_gemini", _gemini_que_falla(503))
    with pytest.raises(errors.APIError):
        await gemini.consultar_gemini_json("prompt")


async def test_un_error_que_no_es_de_disponibilidad_no_pasa_al_respaldo(monkeypatch: pytest.MonkeyPatch, qwen_configurado: None) -> None:
    monkeypatch.setattr(settings, "ia_respaldo", "qwen")
    monkeypatch.setattr(gemini, "_consultar_gemini", _gemini_que_falla(400))
    with pytest.raises(errors.APIError):
        await gemini.consultar_gemini_json("prompt")


async def test_la_medicion_del_oe2_no_usa_el_respaldo(monkeypatch: pytest.MonkeyPatch, qwen_configurado: None) -> None:
    monkeypatch.setattr(settings, "ia_respaldo", "qwen")
    monkeypatch.setattr(gemini, "_consultar_gemini", _gemini_que_falla(429))
    with pytest.raises(errors.APIError):
        await gemini.consultar_gemini_json("prompt", permitir_respaldo=False)


async def test_con_proveedor_qwen_no_se_llama_a_gemini(monkeypatch: pytest.MonkeyPatch, qwen_configurado: None) -> None:
    async def no_llamar(*_a: Any) -> dict[str, Any]:
        raise AssertionError("Con IA_PROVEEDOR=qwen no se llama a Gemini")

    monkeypatch.setattr(settings, "ia_proveedor", "qwen")
    monkeypatch.setattr(gemini, "_consultar_gemini", no_llamar)
    monkeypatch.setattr(qwen.httpx, "AsyncClient", _servidor_qwen('```json\n{"ok": true}\n```'))

    assert await gemini.consultar_gemini_json("prompt") == {"ok": True}


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ('<think>Analizo el CV...</think>\n{"score": 70}', {"score": 70}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('Aquí está el resultado: {"a": 2} Espero que sirva.', {"a": 2}),
    ],
    ids=["con-razonamiento", "bloque-markdown", "texto-alrededor"],
)
def test_extrae_el_json_de_la_respuesta(texto: str, esperado: dict[str, int]) -> None:
    assert qwen.extraer_json(texto) == esperado


@pytest.mark.parametrize("texto", ["no es json", "[1, 2]", ""])
def test_una_respuesta_que_no_es_un_objeto_json_falla(texto: str) -> None:
    with pytest.raises(ValueError):
        qwen.extraer_json(texto)


async def test_un_error_de_autenticacion_de_qwen_no_se_reintenta(monkeypatch: pytest.MonkeyPatch, qwen_configurado: None) -> None:
    vistas: list[httpx.Request] = []
    monkeypatch.setattr(qwen.httpx, "AsyncClient", _servidor_qwen("{}", vistas, estado=401))
    with pytest.raises(httpx.HTTPStatusError):
        await qwen.consultar_qwen_json("prompt")
    assert len(vistas) == 1


@pytest.mark.parametrize(
    "valores",
    [{"ia_proveedor": "otro"}, {"ia_respaldo": "gemini"}, {"ia_respaldo": "qwen"}, {"ia_proveedor": "qwen", "qwen_base_url": "https://x"}],
    ids=["proveedor-desconocido", "respaldo-desconocido", "respaldo-sin-url", "qwen-sin-modelo"],
)
def test_la_configuracion_de_la_ia_se_valida(valores: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        Settings(**{"qwen_base_url": "", "qwen_model": "", **valores})
