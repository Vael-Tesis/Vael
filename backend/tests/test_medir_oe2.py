"""Registros separados del OE2 para Gemini y Qwen (TST-A-06, DEC-026).

Cada medición registra el modelo real y se guarda en la carpeta de su proveedor; la de Qwen
nunca queda registrada como Gemini ni en la carpeta de Gemini.
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

    async def qwen_falso(prompt: str) -> dict[str, Any]:
        llamadas.append(prompt)
        return {"criterios": CRITERIOS, "clasificacion": "recomendado", "resumen": "Bien"}

    async def gemini_prohibido(*_a: Any, **_k: Any) -> dict[str, Any]:
        raise AssertionError("La medición con Qwen no debe llamar a Gemini")

    async def sin_espera(_segundos: float) -> None:
        return None

    monkeypatch.setattr(medir_oe2, "DIRECTORIO_CVS", tmp_path)
    monkeypatch.setattr(medir_oe2, "extraer_texto_pdf", lambda _b: "Python FastAPI PostgreSQL")
    monkeypatch.setattr(medir_oe2, "consultar_qwen_json", qwen_falso)
    monkeypatch.setattr(medir_oe2, "consultar_gemini_json", gemini_prohibido)
    monkeypatch.setattr(medir_oe2.asyncio, "sleep", sin_espera)
    monkeypatch.setattr(settings, "qwen_base_url", "https://api.proveedor.test/v1")
    monkeypatch.setattr(settings, "qwen_model", "qwen-de-prueba")
    monkeypatch.setattr(settings, "qwen_api_key", "clave-de-prueba")
    return llamadas


async def test_la_medicion_con_qwen_registra_el_modelo_real(entorno_medicion: list[str]) -> None:
    resultado = await medir_oe2.medir(proveedor="qwen")

    assert len(entorno_medicion) == len(medir_oe2.CVS) * medir_oe2.EJECUCIONES_POR_CV
    assert resultado["proveedor"] == "qwen"
    assert resultado["modelo"] == "qwen-de-prueba"
    assert resultado["servidor"] == "api.proveedor.test"
    assert resultado["tarea"] == "TST-A-06"
    assert "no con Gemini" in resultado["_comentario"]
    assert {e["modelo"] for e in resultado["ejecuciones"]} == {"qwen-de-prueba"}
    assert {e["proveedor"] for e in resultado["ejecuciones"]} == {"qwen"}
    assert "clave-de-prueba" not in str(resultado)
    assert resultado["resumen_por_cv"]["CV-TI-01"]["desviacion_estandar"] == 0.0


def test_cada_proveedor_tiene_su_propio_registro() -> None:
    assert medir_oe2.directorio_registro("gemini") != medir_oe2.directorio_registro("qwen")
    assert medir_oe2.salida_corrida_completa("gemini") != medir_oe2.salida_corrida_completa("qwen")
    assert medir_oe2.directorio_partes("gemini") != medir_oe2.directorio_partes("qwen")


def test_los_intentos_se_numeran_por_proveedor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(medir_oe2, "DIRECTORIO_METRICAS", tmp_path)
    (tmp_path / "oe2_gemini").mkdir()
    (tmp_path / "oe2_gemini" / "intento_01_cuota_agotada.json").write_text("{}", encoding="utf-8")

    assert medir_oe2._siguiente_ruta_intento("fallo_parcial", "gemini").name == "intento_02_fallo_parcial.json"
    assert medir_oe2._siguiente_ruta_intento("fallo_parcial", "qwen") == tmp_path / "oe2_qwen" / "intento_01_fallo_parcial.json"


async def test_sin_configuracion_de_qwen_no_mide(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "qwen_api_key", "")
    with pytest.raises(SystemExit):
        await medir_oe2.medir(proveedor="qwen")
