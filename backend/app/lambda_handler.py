"""Punto de entrada de la Lambda de análisis (DEC-016, DEC-018, DEV-C-13 · HU-23).

Consume los mensajes de las colas `vael-analisis-cv` y `vael-analisis-entrevista`, ejecuta la
parte de cálculo (`calcular_*`: descarga de S3 y Gemini) y entrega el resultado al backend por
`/api/interno/resultados/...`, firmado con HMAC-SHA256. **No accede a la base de datos**: no
tiene credenciales ni ruta de red hacia RDS (DEC-018).

Si un mensaje falla, se informa en `batchItemFailures` para que SQS lo reintente; tras los
reintentos de la cola termina en su DLQ, que dispara la alarma de CloudWatch (DEC-016, punto 3).

La imagen se construye con `backend/Dockerfile.lambda` y el handler es
`app.lambda_handler.handler`.
"""
import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any


def _cargar_secretos() -> None:
    """Lee las claves de Gemini, del HMAC y de Qwen (respaldo) de Secrets Manager al iniciar.

    Se hace antes de importar la configuración de la aplicación. Así las claves no quedan en
    las variables de entorno de la función, visibles en la consola de AWS.
    """
    arn = os.environ.get("SECRETO_ARN")
    if not arn:
        return
    import boto3

    valores = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"])
    for clave in ("GEMINI_API_KEY", "INTERNAL_SERVICE_KEY", "QWEN_API_KEY"):
        if valores.get(clave):
            os.environ[clave] = valores[clave]


_cargar_secretos()

import httpx  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.interno import CABECERA_FIRMA, CABECERA_MARCA, firmar  # noqa: E402
from app.core.logs import configurar_logging  # noqa: E402
from app.services.analisis_cv import calcular_analisis_cv  # noqa: E402
from app.services.entrevista_ia import calcular_analisis_entrevista  # noqa: E402

configurar_logging()
logger = logging.getLogger("vael.lambda")

Calculo = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

# tipo del mensaje -> (ruta interna del backend, función de cálculo)
TAREAS: dict[str, tuple[str, Calculo]] = {
    "analisis_cv": ("/api/interno/resultados/analisis-cv", calcular_analisis_cv),
    "analisis_entrevista": ("/api/interno/resultados/analisis-entrevista", calcular_analisis_entrevista),
}

# Un solo bucle de eventos para toda la vida del contenedor: el cliente de Gemini se reutiliza
# entre invocaciones y no debe quedar atado a un bucle ya cerrado.
_BUCLE = asyncio.new_event_loop()


async def entregar_resultado(ruta: str, resultado: dict[str, Any]) -> None:
    """Envía el resultado firmado al backend; lanza si no responde 2xx (para que SQS reintente)."""
    if not settings.backend_url_interno:
        raise RuntimeError("Falta BACKEND_URL_INTERNO: no hay a dónde entregar el resultado")
    cuerpo = json.dumps(resultado).encode()
    marca, firma = firmar(cuerpo)
    async with httpx.AsyncClient(timeout=30.0) as cliente:
        respuesta = await cliente.post(
            settings.backend_url_interno.rstrip("/") + ruta,
            content=cuerpo,
            headers={"Content-Type": "application/json", CABECERA_MARCA: marca, CABECERA_FIRMA: firma},
        )
    respuesta.raise_for_status()


async def procesar_mensaje(mensaje: dict[str, Any]) -> None:
    """Calcula y entrega un mensaje. Un mensaje sin tipo conocido o sin tenant se rechaza (DEC-016)."""
    tipo = mensaje.get("tipo")
    if tipo not in TAREAS:
        raise ValueError(f"Mensaje con tipo desconocido: {tipo!r}")
    if not mensaje.get("tenant_id"):
        raise ValueError("Mensaje sin tenant_id")
    ruta, calcular = TAREAS[tipo]
    resultado = await calcular(mensaje)
    await entregar_resultado(ruta, resultado)


def handler(event: dict[str, Any], _context: Any) -> dict[str, list[dict[str, str]]]:
    """Procesa un lote de SQS y devuelve los mensajes fallidos (ReportBatchItemFailures)."""
    fallidos: list[dict[str, str]] = []
    for registro in event.get("Records", []):
        try:
            mensaje = json.loads(registro["body"])
            _BUCLE.run_until_complete(procesar_mensaje(mensaje))
            logger.info("Mensaje procesado", extra={"operation": f"lambda_{mensaje.get('tipo')}", "tenant_id": mensaje.get("tenant_id")})
        except Exception:
            logger.exception("Falló el mensaje %s; SQS lo reintentará", registro.get("messageId"))
            fallidos.append({"itemIdentifier": registro["messageId"]})
    return {"batchItemFailures": fallidos}
