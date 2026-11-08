"""Despachador único de tareas asíncronas (DEC-016, tarea DEV-C-13).

Los routers y servicios no llaman a SQS ni a BackgroundTasks directamente: usan
`despachar_tarea(tipo, payload)`. Cada payload lleva el `tenant_id` (DEC-016, punto 6) y el
identificador de la entidad a procesar, y debe ser serializable a JSON para poder viajar
en un mensaje de SQS.

Dos modos (`DESPACHO_MODO`, HU-23):
- **en_proceso** (desarrollo y tests): la tarea corre en segundo plano en el mismo proceso,
  sin bloquear la respuesta HTTP: preparación, cálculo y aplicación seguidos.
- **sqs** (producción): el backend prepara el mensaje con todo lo que el cálculo necesita y
  lo publica en la cola del tipo; la Lambda calcula sin tocar la base de datos y entrega el
  resultado firmado por /api/interno (DEC-018). Los llamadores no cambian.
"""
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from app.core.config import settings
from app.core.database import con_tenant, sesion_con_tenant
from app.services import aws_services

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


def _cola(tipo: TipoTarea) -> str:
    """URL de la cola de SQS de cada tipo (DEC-016: vael-analisis-cv y vael-analisis-entrevista)."""
    if tipo is TipoTarea.ANALISIS_CV:
        return settings.sqs_url_analisis_cv
    return settings.sqs_url_analisis_entrevista


async def _preparar_mensaje(tipo: TipoTarea, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Arma el mensaje de SQS con los datos de la base (como vael_app, con el tenant fijado).

    Devuelve None si el registro ya no existe o no tiene nada que analizar.
    """
    async with sesion_con_tenant(payload["tenant_id"]) as db:
        if tipo is TipoTarea.ANALISIS_CV:
            from app.services.analisis_cv import cargar_para_analisis_cv, preparar_mensaje_analisis_cv

            cargado_cv = await cargar_para_analisis_cv(payload["candidato_id"], db)
            return preparar_mensaje_analisis_cv(*cargado_cv) if cargado_cv else None

        from app.services.entrevista_ia import cargar_para_analisis_entrevista, preparar_mensaje_analisis_entrevista

        cargado = await cargar_para_analisis_entrevista(payload["entrevista_id"], db)
        return preparar_mensaje_analisis_entrevista(*cargado) if cargado else None


async def _publicar(tipo: TipoTarea, payload: dict[str, Any]) -> None:
    """Modo sqs: prepara el mensaje y lo publica en la cola del tipo."""
    mensaje = await _preparar_mensaje(tipo, payload)
    if mensaje is None:
        logger.warning("La tarea %s no se publicó: no hay datos que analizar", tipo, extra={"tenant_id": payload["tenant_id"]})
        return
    mensaje_id = await aws_services.encolar_tarea(_cola(tipo), mensaje)
    logger.info(
        "Tarea %s publicada en SQS (%s)",
        tipo,
        mensaje_id,
        extra={"operation": f"despacho_{tipo}", "tenant_id": payload["tenant_id"]},
    )


async def despachar_tarea(tipo: TipoTarea | str, payload: dict[str, Any]) -> asyncio.Task[None]:
    """Programa una tarea asíncrona y devuelve de inmediato.

    Devuelve la tarea de asyncio para que las pruebas puedan esperarla; el código de la
    aplicación no la necesita.
    """
    tipo = TipoTarea(tipo)
    _validar_payload(tipo, payload)
    en_sqs = settings.despacho_modo == "sqs"
    manejador: Manejador = (lambda datos: _publicar(tipo, datos)) if en_sqs else _manejador(tipo)
    tarea = asyncio.create_task(_ejecutar(tipo, manejador, payload), name=f"vael:{tipo}")
    _tareas_en_curso.add(tarea)
    tarea.add_done_callback(_tareas_en_curso.discard)
    logger.info(
        "Tarea %s despachada %s",
        tipo,
        "a SQS" if en_sqs else "en proceso",
        extra={"operation": f"despacho_{tipo}", "tenant_id": payload["tenant_id"]},
    )
    return tarea
