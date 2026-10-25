"""Pruebas del despachador único de tareas (DEC-016, DEV-C-13, modo en proceso)."""
import inspect
import logging
from typing import Any

import pytest

from app.core import despacho
from app.core.despacho import TipoTarea, despachar_tarea
from app.routers import candidatos, entrevista, publico


@pytest.fixture
def ejecutadas(monkeypatch: pytest.MonkeyPatch) -> list[tuple[TipoTarea, dict[str, Any]]]:
    """Reemplaza los manejadores reales por uno que registra lo que recibe."""
    registro: list[tuple[TipoTarea, dict[str, Any]]] = []

    def manejador_falso(tipo: TipoTarea) -> despacho.Manejador:
        async def ejecutar(payload: dict[str, Any]) -> None:
            registro.append((tipo, payload))

        return ejecutar

    monkeypatch.setattr(despacho, "_manejador", manejador_falso)
    return registro


async def test_ejecuta_la_tarea_con_su_payload(ejecutadas: list[Any]) -> None:
    """La tarea corre en proceso con el payload recibido."""
    payload = {"tenant_id": "t1", "candidato_id": "c1"}
    tarea = await despachar_tarea(TipoTarea.ANALISIS_CV, payload)
    await tarea
    assert ejecutadas == [(TipoTarea.ANALISIS_CV, payload)]


async def test_acepta_el_tipo_como_texto(ejecutadas: list[Any]) -> None:
    """El tipo puede llegar como texto (por ejemplo, desde un mensaje de SQS)."""
    tarea = await despachar_tarea("analisis_entrevista", {"tenant_id": "t1", "entrevista_id": "e1"})
    await tarea
    assert ejecutadas[0][0] is TipoTarea.ANALISIS_ENTREVISTA


@pytest.mark.parametrize(
    ("tipo", "payload"),
    [
        (TipoTarea.ANALISIS_CV, {"candidato_id": "c1"}),
        (TipoTarea.ANALISIS_CV, {"tenant_id": "t1"}),
        (TipoTarea.ANALISIS_ENTREVISTA, {"tenant_id": "t1", "candidato_id": "c1"}),
    ],
)
async def test_exige_tenant_e_identificador(ejecutadas: list[Any], tipo: TipoTarea, payload: dict[str, Any]) -> None:
    """Sin tenant_id o sin el identificador del tipo, el despacho se rechaza (DEC-016, punto 6)."""
    with pytest.raises(ValueError):
        await despachar_tarea(tipo, payload)
    assert ejecutadas == []


async def test_exige_payload_serializable(ejecutadas: list[Any]) -> None:
    """El payload debe poder viajar como JSON en un mensaje de SQS."""
    with pytest.raises(ValueError, match="serializable"):
        await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": "t1", "candidato_id": "c1", "objeto": object()})


async def test_rechaza_tipos_desconocidos() -> None:
    """Un tipo fuera del catálogo no se despacha."""
    with pytest.raises(ValueError):
        await despachar_tarea("tipo_inexistente", {"tenant_id": "t1"})


async def test_una_falla_se_registra_sin_propagarse(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Si la tarea falla, queda en el log con su tenant y no tumba el proceso."""

    def manejador_que_falla(_tipo: TipoTarea) -> despacho.Manejador:
        async def ejecutar(_payload: dict[str, Any]) -> None:
            raise RuntimeError("falla simulada")

        return ejecutar

    monkeypatch.setattr(despacho, "_manejador", manejador_que_falla)
    with caplog.at_level(logging.ERROR, logger="app.core.despacho"):
        tarea = await despachar_tarea(TipoTarea.ANALISIS_CV, {"tenant_id": "t1", "candidato_id": "c1"})
        await tarea
    assert any("falló" in r.getMessage() for r in caplog.records)


def test_manejadores_reales_existen_para_cada_tipo() -> None:
    """Cada tipo del catálogo resuelve a una función ejecutable."""
    for tipo in TipoTarea:
        assert callable(despacho._manejador(tipo))


@pytest.mark.parametrize("modulo", [candidatos, publico, entrevista])
def test_los_routers_de_analisis_no_usan_background_tasks(modulo: Any) -> None:
    """Los análisis se despachan con despachar_tarea, nunca con BackgroundTasks (DEC-016)."""
    codigo = inspect.getsource(modulo)
    assert "BackgroundTasks" not in codigo
    assert "despachar_tarea" in codigo
