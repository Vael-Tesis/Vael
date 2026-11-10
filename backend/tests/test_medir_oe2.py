"""Medición del OE2 con el proveedor de respaldo (TST-A-06, DEC-026).

La medición con otro modelo debe registrar ese modelo y su servidor, y nunca quedar como
`gemini-3.8-flash` ni en el archivo reservado a Gemini.
"""
from pathlib import Path
from typing import Any

import pytest

from app.core.config import settings
from app.scripts import medir_oe2

CRITERIOS = {
    "match_habilidades": {"puntaje": 30, "justificacion": "a"},
    "experiencia": {"puntaje": 15, "justificacion": "b"},
    "formacion": {"puntaje": 10, "justificacion": "c"},
    "coherencia": {"puntaje": 10, "justificacion": "d"},
    "trayectoria": {"puntaje": 5, "justificacion": "e"},
}


@pytest.fixture
def entorno_medicion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    for cv in medir_oe2.CVS:
        (tmp_path / f"{cv}.pdf").write_bytes(b"%PDF")
    llamadas: list[str] = []

    async def respaldo_falso(prompt: str) -> dict[str, Any]:
        llamadas.append(prompt)
        return {"criterios": CRITERIOS, "clasificacion": "recomendado", "resumen": "Bien"}

    async def gemini_prohibido(*_a: Any, **_k: Any) -> dict[str, Any]:
        raise AssertionError("La medición con el respaldo no debe llamar a Gemini")

    async def sin_espera(_segundos: float) -> None:
        return None

    monkeypatch.setattr(medir_oe2, "DIRECTORIO_CVS", tmp_path)
    monkeypatch.setattr(medir_oe2, "extraer_texto_pdf", lambda _b: "Python FastAPI PostgreSQL")
    monkeypatch.setattr(medir_oe2, "consultar_qwen_json", respaldo_falso)
    monkeypatch.setattr(medir_oe2, "consultar_gemini_json", gemini_prohibido)
    monkeypatch.setattr(medir_oe2.asyncio, "sleep", sin_espera)
    monkeypatch.setattr(settings, "qwen_base_url", "https://api.proveedor.test/v1")
    monkeypatch.setattr(settings, "qwen_model", "modelo-respaldo")
    monkeypatch.setattr(settings, "qwen_api_key", "clave-de-prueba")
    return llamadas


async def test_la_medicion_con_el_respaldo_registra_el_modelo_real(entorno_medicion: list[str]) -> None:
    resultado = await medir_oe2.medir(proveedor="respaldo")

    assert len(entorno_medicion) == len(medir_oe2.CVS) * medir_oe2.EJECUCIONES_POR_CV
    assert resultado["proveedor"] == "respaldo"
    assert resultado["modelo"] == "modelo-respaldo"
    assert resultado["servidor"] == "api.proveedor.test"
    assert "NO CON GEMINI" in resultado["_comentario"]
    assert {e["modelo"] for e in resultado["ejecuciones"]} == {"modelo-respaldo"}
    assert {e["proveedor"] for e in resultado["ejecuciones"]} == {"respaldo"}
    assert "clave-de-prueba" not in str(resultado)
    assert resultado["resumen_por_cv"]["CV-TI-01"]["desviacion_estandar"] == 0.0


def test_el_archivo_del_respaldo_no_es_el_de_gemini() -> None:
    assert medir_oe2.SALIDA_CORRIDA_RESPALDO != medir_oe2.SALIDA_CORRIDA_COMPLETA


async def test_sin_configuracion_del_respaldo_no_mide(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "qwen_api_key", "")
    with pytest.raises(SystemExit):
        await medir_oe2.medir(proveedor="respaldo")
