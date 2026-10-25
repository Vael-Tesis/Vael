"""Logs estructurados en JSON (DEV-C-08): una línea por evento, lista para CloudWatch.

Cada línea lleva timestamp UTC, nivel, logger y mensaje; además, tenant_id cuando la
petición o la tarea lo fijaron, y operation / duration_ms cuando se mide una operación
(métrica M-01 del plan de métricas). Los campos adicionales se pasan con `extra={...}`.
"""
import json
import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Tenant de la petición o tarea en curso; lo fijan las dependencias de autenticación y
# las tareas en segundo plano, y el formateador lo agrega a cada línea.
tenant_actual: ContextVar[str | None] = ContextVar("tenant_actual", default=None)

CAMPOS_EXTRA: tuple[str, ...] = (
    "tenant_id",
    "operation",
    "duration_ms",
    "resultado",
    "candidato_id",
    "entrevista_id",
    "method",
    "path",
    "status_code",
)


class FormateadorJSON(logging.Formatter):
    """Convierte cada registro de logging en un objeto JSON de una línea."""

    def format(self, record: logging.LogRecord) -> str:
        """Serializa el registro con los campos base y los extra que traiga."""
        datos: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for campo in CAMPOS_EXTRA:
            valor = getattr(record, campo, None)
            if valor is not None:
                datos[campo] = valor
        if "tenant_id" not in datos and (tenant := tenant_actual.get()):
            datos["tenant_id"] = tenant
        if record.exc_info:
            datos["exception"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    """Envía todos los logs, incluidos los de Uvicorn, a stdout en formato JSON.

    El log de acceso de Uvicorn se desactiva porque el middleware de peticiones ya registra
    cada request con su duración y su tenant.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormateadorJSON())
    raiz = logging.getLogger()
    raiz.handlers = [handler]
    raiz.setLevel(nivel)
    for nombre in ("uvicorn", "uvicorn.error"):
        logger_uvicorn = logging.getLogger(nombre)
        logger_uvicorn.handlers = []
        logger_uvicorn.propagate = True
    logging.getLogger("uvicorn.access").disabled = True


@contextmanager
def medir_operacion(logger: logging.Logger, operation: str, **campos: Any) -> Iterator[None]:
    """Registra la duración de una operación con su resultado (ok / error).

    Uso:
        with medir_operacion(logger, "analisis_cv", candidato_id=id):
            ...
    """
    inicio = time.perf_counter()
    resultado = "ok"
    try:
        yield
    except Exception:
        resultado = "error"
        raise
    finally:
        duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
        logger.info(
            "Operación %s terminada (%s)",
            operation,
            resultado,
            extra={"operation": operation, "duration_ms": duracion_ms, "resultado": resultado, **campos},
        )
