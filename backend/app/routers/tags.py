"""Endpoints de etiquetas de la empresa — /api/tags/ (DEV-A-01, HU-13)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_rol
from app.models.candidato import Tag
from app.models.usuario import RolUsuario, Usuario
from app.schemas.candidato import MensajeResponse
from app.schemas.tag import TagCreateRequest, TagResponse, TagUpdateRequest
from app.services import candidatos as servicio_candidatos

router = APIRouter(prefix="/api/tags", tags=["tags"])

_RECLUTADOR_O_SUPERIOR = (RolUsuario.ADMIN, RolUsuario.GERENTE, RolUsuario.RECLUTADOR)
_ADMIN_O_GERENTE = (RolUsuario.ADMIN, RolUsuario.GERENTE)


async def _tag_del_tenant(tag_id: str, tenant_id: str, db: AsyncSession) -> Tag:
    tag = (await db.exec(select(Tag).where(Tag.tenant_id == tenant_id, Tag.id == tag_id))).first()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etiqueta no encontrada")
    return tag


async def _exigir_nombre_libre(nombre: str, tenant_id: str, db: AsyncSession, excepto_id: str | None = None) -> None:
    """El nombre de la etiqueta es único en la empresa, sin distinguir mayúsculas (409)."""
    statement = select(Tag).where(Tag.tenant_id == tenant_id, func.lower(Tag.nombre) == nombre.strip().lower())
    if excepto_id is not None:
        statement = statement.where(Tag.id != excepto_id)
    if (await db.exec(statement)).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Ya existe la etiqueta {nombre.strip()}")


@router.get("", response_model=list[TagResponse])
async def listar_tags(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Tag]:
    """Lista las etiquetas de la empresa, por nombre."""
    statement = select(Tag).where(Tag.tenant_id == actor.tenant_id).order_by(Tag.nombre)
    return list((await db.exec(statement)).all())


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def crear_tag(
    body: TagCreateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tag:
    """Crea una etiqueta; 409 si el nombre ya existe en la empresa."""
    await _exigir_nombre_libre(body.nombre, actor.tenant_id, db)
    tag = Tag(tenant_id=actor.tenant_id, nombre=body.nombre.strip(), color=body.color)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.put("/{tag_id}", response_model=TagResponse)
async def editar_tag(
    tag_id: str,
    body: TagUpdateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tag:
    """Edita el nombre o el color de una etiqueta."""
    tag = await _tag_del_tenant(tag_id, actor.tenant_id, db)
    if body.nombre is not None:
        await _exigir_nombre_libre(body.nombre, actor.tenant_id, db, excepto_id=tag.id)
        tag.nombre = body.nombre.strip()
    if "color" in body.model_fields_set:
        tag.color = body.color
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}", response_model=MensajeResponse)
async def eliminar_tag(
    tag_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Elimina la etiqueta y sus asignaciones."""
    try:
        await servicio_candidatos.eliminar_tag(tag_id, actor.tenant_id, db)
    except servicio_candidatos.ErrorCandidatos as error:
        raise HTTPException(status_code=error.codigo, detail=error.detalle) from error
    return MensajeResponse(detail="Etiqueta eliminada")
