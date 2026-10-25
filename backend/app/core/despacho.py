"""Despachador único de tareas asíncronas (DEC-016, tarea DEV-C-13).

Los routers y servicios no llaman a SQS ni a BackgroundTasks directamente: usan
`despachar_tarea(tipo, payload)`. Cada payload lleva el `tenant_id` (DEC-016, punto 6) y el
identificador de la entidad a procesar, y debe ser serializable a JSON para poder viajar
en un mensaje de SQS.

Modo actual: **en proceso**. La tarea corre en segundo plano en el mismo proceso, sin
bloquear la respuesta HTTP. El modo SQS + Lambda de producción se agrega en HU-23 detrás de
esta misma función, así que los llamadores no cambian.
"""
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from app.core.database import con_tenant

logger = logging.getLogger(__name__)


class TipoTarea(StrEnum):
    """Tareas asíncronas de VAEL; cada una tendrá su cola de SQS en producción (DEC-016)."""

    ANALISIS_CV = "analisis_cv"
    ANALISIS_ENTREVISTA = "analisis_entrevista"


# Identificador obligatorio en el payload de cada tipo, además de tenant_id
CAMPO_ID: dict[TipoTarea, str] = {
    TipoTarea.ANALISIS_CV: "candidato_id",
    TipoTarea.ANALISIS_ENTREVISTA: "entrevista_id",
}

Manejador = Callable[[dict[str, Any]], Awaitable[None]]

# Referencias a las tareas en curso: sin ellas, asyncio puede recolectarlas antes de terminar
_tareas_en_curso: set[asyncio.Task[None]] = set()


def _manejador(tipo: TipoTarea) -> Manejador:
    """Función que ejecuta cada tipo de tarea (import diferido: los servicios importan core)."""
    if tipo is TipoTarea.ANALISIS_CV:
        from app.services.analisis_cv import analizar_cv_candidato

        return lambda payload: analizar_cv_candidato(payload["candidato_id"])
    from app.services.entrevista_ia import analizar_entrevista_candidato

    return lambda payload: analizar_entrevista_candidato(payload["entrevista_id"])


def _validar_payload(tipo: TipoTarea, payload: dict[str, Any]) -> None:
    """Exige tenant_id y el identificador del tipo, y que el payload sea serializable a JSON."""
    faltantes = [campo for campo in ("tenant_id", CAMPO_ID[tipo]) if not payload.get(campo)]
    if faltantes:
        raise ValueError(f"Payload de {tipo} sin {', '.join(faltantes)}")
    try:
        json.dumps(payload)
    except TypeError as exc:
        raise ValueError(f"El payload de {tipo} debe ser serializable a JSON") from exc


async def _ejecutar(tipo: TipoTarea, manejador: Manejador, payload: dict[str, Any]) -> None:
    """Corre la tarea con el tenant del mensaje fijado (DEC-010, DEC-016 punto 6) y registra
    cualquier falla no controlada, sin propagarla.

    El tenant sale del payload y no del contexto de la petición que la despachó: así la
    tarea se comporta igual en proceso que cuando llegue desde SQS.
    """
    try:
        with con_tenant(payload["tenant_id"]):
            await manejador(payload)
    except Exception:
        logger.exception("La tarea %s falló", tipo, extra={"tenant_id": payload.get("tenant_id")})


async def despachar_tarea(tipo: TipoTarea | str, payload: dict[str, Any]) -> asyncio.Task[None]:
    """Programa una tarea asíncrona y devuelve de inmediato.

    Devuelve la tarea de asyncio para que las pruebas puedan esperarla; el código de la
    aplicación no la necesita.
    """
    tipo = TipoTarea(tipo)
    _validar_payload(tipo, payload)
    tarea = asyncio.create_task(_ejecutar(tipo, _manejador(tipo), payload), name=f"vael:{tipo}")
    _tareas_en_curso.add(tarea)
    tarea.add_done_callback(_tareas_en_curso.discard)
    logger.info(
        "Tarea %s despachada en proceso",
        tipo,
        extra={"operation": f"despacho_{tipo}", "tenant_id": payload["tenant_id"]},
    )
    return tarea
