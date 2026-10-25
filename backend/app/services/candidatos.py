"""Servicio de candidatos: notas internas y etiquetas (DEV-A-01, HU-13; doc 08).

Reglas: solo el autor edita su nota; el autor o un admin la eliminan. Asignar una etiqueta
es idempotente. Las notas nunca son visibles para el candidato.

No depende de FastAPI: lanza ErrorCandidatos y el router la traduce a HTTP.
"""
from io import BytesIO
from pathlib import Path

from PyPDF2 import PdfReader
from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.base import utcnow
from app.models.candidato import Candidato, CandidatoTag, NotaCandidato, Tag
from app.models.usuario import RolUsuario, Usuario


TAMANO_MAXIMO_CV = 10 * 1024 * 1024  # 10 MB


def motivo_de_rechazo_cv(nombre: str | None, contenido: bytes) -> str | None:
    """Motivo por el que un archivo no sirve como CV, o None si es un PDF legible (RF-A-09).

    Un PDF escaneado (sin texto) sí se acepta: el análisis lo deja para revisión manual.
    """
    if not contenido:
        return "El archivo está vacío"
    if len(contenido) > TAMANO_MAXIMO_CV:
        return "El archivo supera los 10 MB"
    if Path(nombre or "").suffix.lower() != ".pdf" or not contenido.startswith(b"%PDF"):
        return "No es un PDF"
    try:
        PdfReader(BytesIO(contenido))
    except Exception:
        return "El PDF está dañado o no se puede leer"
    return None


class ErrorCandidatos(Exception):
    """Operación rechazada. `codigo` es el estado HTTP que debe responder el router."""

    def __init__(self, codigo: int, detalle: str) -> None:
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


async def _nota(candidato_id: str, nota_id: str, tenant_id: str, db: AsyncSession) -> NotaCandidato:
    statement = select(NotaCandidato).where(
        NotaCandidato.tenant_id == tenant_id,
        NotaCandidato.candidato_id == candidato_id,
        NotaCandidato.id == nota_id,
    )
    nota = (await db.exec(statement)).first()
    if nota is None:
        raise ErrorCandidatos(404, "Nota no encontrada")
    return nota


async def editar_nota(candidato_id: str, nota_id: str, contenido: str, actor: Usuario, db: AsyncSession) -> NotaCandidato:
    """Solo el autor edita su nota; actualiza updated_at."""
    nota = await _nota(candidato_id, nota_id, actor.tenant_id, db)
    if nota.autor_id != actor.id:
        raise ErrorCandidatos(403, "Solo el autor puede editar la nota")
    nota.contenido = contenido
    nota.updated_at = utcnow()
    db.add(nota)
    await db.commit()
    await db.refresh(nota)
    return nota


async def eliminar_nota(candidato_id: str, nota_id: str, actor: Usuario, db: AsyncSession) -> None:
    """El autor o un admin eliminan la nota."""
    nota = await _nota(candidato_id, nota_id, actor.tenant_id, db)
    if nota.autor_id != actor.id and actor.rol != RolUsuario.ADMIN:
        raise ErrorCandidatos(403, "Solo el autor o un administrador pueden eliminar la nota")
    await db.delete(nota)
    await db.commit()


async def _tag(tag_id: str, tenant_id: str, db: AsyncSession) -> Tag:
    tag = (await db.exec(select(Tag).where(Tag.tenant_id == tenant_id, Tag.id == tag_id))).first()
    if tag is None:
        raise ErrorCandidatos(404, "Etiqueta no encontrada")
    return tag


async def etiquetas_de(candidato_id: str, tenant_id: str, db: AsyncSession) -> list[Tag]:
    """Etiquetas asignadas a un candidato, por nombre."""
    statement = (
        select(Tag)
        .join(CandidatoTag, CandidatoTag.tag_id == Tag.id)
        .where(Tag.tenant_id == tenant_id, CandidatoTag.tenant_id == tenant_id, CandidatoTag.candidato_id == candidato_id)
        .order_by(Tag.nombre)
    )
    return list((await db.exec(statement)).all())


async def asignar_etiqueta(candidato: Candidato, tag_id: str, db: AsyncSession) -> list[Tag]:
    """Asigna la etiqueta al candidato; si ya la tenía, no hace nada (idempotente)."""
    tag = await _tag(tag_id, candidato.tenant_id, db)
    existente = await db.get(CandidatoTag, (candidato.id, tag.id))
    if existente is None:
        db.add(CandidatoTag(tenant_id=candidato.tenant_id, candidato_id=candidato.id, tag_id=tag.id))
        await db.commit()
    return await etiquetas_de(candidato.id, candidato.tenant_id, db)


async def quitar_etiqueta(candidato: Candidato, tag_id: str, db: AsyncSession) -> list[Tag]:
    """Quita la etiqueta del candidato; 404 si no la tenía."""
    asignacion = await db.get(CandidatoTag, (candidato.id, tag_id))
    if asignacion is None or asignacion.tenant_id != candidato.tenant_id:
        raise ErrorCandidatos(404, "El candidato no tiene esa etiqueta")
    await db.delete(asignacion)
    await db.commit()
    return await etiquetas_de(candidato.id, candidato.tenant_id, db)


async def eliminar_tag(tag_id: str, tenant_id: str, db: AsyncSession) -> None:
    """Elimina la etiqueta y sus asignaciones (doc 06)."""
    tag = await _tag(tag_id, tenant_id, db)
    await db.exec(delete(CandidatoTag).where(CandidatoTag.tenant_id == tenant_id, CandidatoTag.tag_id == tag.id))
    await db.delete(tag)
    await db.commit()
