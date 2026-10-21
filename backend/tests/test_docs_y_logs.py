"""Pruebas de DEV-C-07 (/docs solo con DEBUG) y DEV-C-08 (logs JSON con tenant y duración)."""
import importlib
import json
import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.main as modulo_main
from app.core.config import Settings, settings
from app.core.logs import FormateadorJSON, medir_operacion, tenant_actual

_REQUERIDOS = {"database_url": "sqlite+aiosqlite://", "secret_key": "x" * 32, "internal_service_key": "k"}


# --- DEV-C-07 -----------------------------------------------------------------


def test_debug_activo_en_produccion_no_arranca() -> None:
    """ENVIRONMENT=production con DEBUG=true se rechaza al cargar la configuración."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", debug=True, **_REQUERIDOS)


def test_produccion_sin_debug_es_valida() -> None:
    """ENVIRONMENT=production con DEBUG=false es la configuración esperada."""
    config = Settings(_env_file=None, environment="production", debug=False, **_REQUERIDOS)
    assert config.is_production and not config.debug


@pytest.fixture
def app_sin_debug(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Reconstruye la app con DEBUG=false y la restaura al terminar."""
    monkeypatch.setattr(settings, "debug", False)
    modulo = importlib.reload(modulo_main)
    try:
        yield TestClient(modulo.app)
    finally:
        monkeypatch.undo()
        importlib.reload(modulo_main)


def test_docs_deshabilitado_sin_debug(app_sin_debug: TestClient) -> None:
    """Con DEBUG=false no existen /docs ni /redoc."""
    assert app_sin_debug.get("/docs").status_code == 404
    assert app_sin_debug.get("/redoc").status_code == 404
    assert app_sin_debug.get("/health").status_code == 200


# --- DEV-C-08 -----------------------------------------------------------------


def _registro(mensaje: str, **extra: object) -> logging.LogRecord:
    registro = logging.LogRecord("vael.test", logging.INFO, __file__, 1, mensaje, None, None)
    for clave, valor in extra.items():
        setattr(registro, clave, valor)
    return registro


def test_formateador_produce_json_con_campos_extra() -> None:
    """Cada línea es JSON válido con los campos base y los extra que traiga el registro."""
    linea = FormateadorJSON().format(_registro("hola", operation="analisis_cv", duration_ms=12.5))
    datos = json.loads(linea)
    assert datos["message"] == "hola"
    assert datos["level"] == "INFO"
    assert datos["operation"] == "analisis_cv"
    assert datos["duration_ms"] == 12.5
    assert "timestamp" in datos


def test_formateador_agrega_el_tenant_del_contexto() -> None:
    """Si la petición o la tarea fijó el tenant, aparece en la línea aunque no venga en extra."""
    token = tenant_actual.set("tenant-a")
    try:
        datos = json.loads(FormateadorJSON().format(_registro("con tenant")))
    finally:
        tenant_actual.reset(token)
    assert datos["tenant_id"] == "tenant-a"


def test_medir_operacion_registra_duracion_y_resultado(caplog: pytest.LogCaptureFixture) -> None:
    """La operación exitosa queda con resultado ok y su duración en milisegundos."""
    logger = logging.getLogger("vael.test")
    with caplog.at_level(logging.INFO, logger="vael.test"), medir_operacion(logger, "analisis_cv", candidato_id="c1"):
        pass
    registro = caplog.records[-1]
    assert registro.operation == "analisis_cv"
    assert registro.resultado == "ok"
    assert registro.candidato_id == "c1"
    assert registro.duration_ms >= 0


def test_medir_operacion_marca_error_y_propaga(caplog: pytest.LogCaptureFixture) -> None:
    """Si la operación falla, se registra con resultado error y la excepción no se oculta."""
    logger = logging.getLogger("vael.test")
    with caplog.at_level(logging.INFO, logger="vael.test"), pytest.raises(RuntimeError):
        with medir_operacion(logger, "analisis_cv"):
            raise RuntimeError("falla simulada")
    assert caplog.records[-1].resultado == "error"


def test_middleware_registra_cada_peticion(caplog: pytest.LogCaptureFixture) -> None:
    """Cada request deja una línea con método, ruta, estado y duración."""
    with caplog.at_level(logging.INFO, logger="vael.http"):
        TestClient(modulo_main.app).get("/health")
    registro = next(r for r in reversed(caplog.records) if r.name == "vael.http")
    assert registro.operation == "GET /health"
    assert registro.status_code == 200
    assert registro.duration_ms >= 0
