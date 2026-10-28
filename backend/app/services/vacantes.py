"""Servicio de vacantes: estados, eliminación en borrador y textos de publicación (DEV-A-04; doc 08).

No depende de FastAPI: lanza ErrorVacante y el router la traduce a HTTP.
"""
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.base import utcnow
from app.models.candidato import Candidato
from app.models.vacante import EstadoVacante, Vacante


class ErrorVacante(Exception):
    """Operación rechazada. `codigo` es el estado HTTP que debe responder el router."""

    def __init__(self, codigo: int, detalle: str) -> None:
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


# Desde qué estados se llega a cada uno (HU-09). Publicar desde pausada es "reactivar" y
# pausar es "despublicar" (doc 15). Cerrada es final: para reabrir, se duplica.
TRANSICIONES: dict[EstadoVacante, frozenset[EstadoVacante]] = {
    EstadoVacante.ABIERTA: frozenset({EstadoVacante.BORRADOR, EstadoVacante.PAUSADA}),
    EstadoVacante.PAUSADA: frozenset({EstadoVacante.ABIERTA}),
    EstadoVacante.CERRADA: frozenset({EstadoVacante.ABIERTA, EstadoVacante.PAUSADA}),
}

_NOMBRE = {
    EstadoVacante.BORRADOR: "en borrador",
    EstadoVacante.ABIERTA: "abierta",
    EstadoVacante.PAUSADA: "pausada",
    EstadoVacante.CERRADA: "cerrada",
}


async def cambiar_estado(vacante: Vacante, destino: EstadoVacante, db: AsyncSession) -> Vacante:
    """Aplica una transición válida; 409 si la vacante está en un estado desde el que no se llega."""
    if vacante.estado == destino:
        return vacante
    if vacante.estado not in TRANSICIONES[destino]:
        raise ErrorVacante(409, f"Una vacante {_NOMBRE[vacante.estado]} no puede pasar a {_NOMBRE[destino]}")
    vacante.estado = destino
    vacante.updated_at = utcnow()
    db.add(vacante)
    await db.commit()
    await db.refresh(vacante)
    return vacante


async def eliminar_vacante(vacante: Vacante, db: AsyncSession) -> None:
    """Solo se elimina una vacante en borrador y sin candidatos (409 en otro caso)."""
    if vacante.estado != EstadoVacante.BORRADOR:
        raise ErrorVacante(409, "Solo se puede eliminar una vacante en borrador; ciérrala en su lugar")
    con_candidatos = select(Candidato.id).where(Candidato.tenant_id == vacante.tenant_id, Candidato.vacante_id == vacante.id)
    if (await db.exec(con_candidatos)).first() is not None:
        raise ErrorVacante(409, "La vacante tiene candidatos y no se puede eliminar")
    await db.delete(vacante)
    await db.commit()


async def guardar_textos_publicacion(vacante: Vacante, textos: dict[str, str], db: AsyncSession) -> dict[str, str]:
    """Guarda los textos de difusión editados por RRHH, por canal."""
    vacante.textos_publicacion = {canal: texto for canal, texto in textos.items() if texto.strip()}
    vacante.updated_at = utcnow()
    db.add(vacante)
    await db.commit()
    await db.refresh(vacante)
    return vacante.textos_publicacion or {}
