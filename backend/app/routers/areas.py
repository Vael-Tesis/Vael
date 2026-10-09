"""Endpoints de gestión de áreas/departamentos — /api/areas/."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_rol
from app.models.area import Area
from app.models.base import utcnow
from app.models.usuario import RolUsuario, Usuario
from app.schemas.area import AreaCreateRequest, AreaResponse, AreaUpdateRequest

router = APIRouter(prefix="/api/areas", tags=["areas"])

_ADMIN_O_GERENTE = (RolUsuario.ADMIN, RolUsuario.GERENTE)


async def _obtener_area_del_tenant(area_id: str, tenant_id: str, db: AsyncSession) -> Area:
    """Busca un área por id dentro del tenant actual, o lanza 404 si no existe."""
    statement = select(Area).where(Area.id == area_id, Area.tenant_id == tenant_id)
    result = await db.exec(statement)
    area = result.first()

    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área no encontrada")

    return area


@router.get("", response_model=list[AreaResponse])
async def listar_areas(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    activa: bool | None = None,
) -> list[Area]:
    """Lista las áreas del tenant, con filtro opcional por estado activa."""
    statement = select(Area).where(Area.tenant_id == actor.tenant_id)

    if activa is not None:
        statement = statement.where(Area.activa == activa)

    result = await db.exec(statement)
    return list(result.all())


@router.post("", response_model=AreaResponse, status_code=status.HTTP_201_CREATED)
async def crear_area(
    body: AreaCreateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Area:
    """Crea un área o departamento para el tenant actual."""
    area = Area(tenant_id=actor.tenant_id, **body.model_dump())
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return area


@router.get("/{area_id}", response_model=AreaResponse)
async def obtener_area(
    area_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Area:
    """Retorna el detalle de un área."""
    return await _obtener_area_del_tenant(area_id, actor.tenant_id, db)


@router.put("/{area_id}", response_model=AreaResponse)
async def editar_area(
    area_id: str,
    body: AreaUpdateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Area:
    """Edita los campos provistos de un área (actualización parcial).

    Sin DELETE: las vacantes referencian area_id, así que desactivar (activa=false)
    es la forma de retirar un área sin dejar huérfanas las vacantes existentes.
    """
    area = await _obtener_area_del_tenant(area_id, actor.tenant_id, db)

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(area, campo, valor)

    area.updated_at = utcnow()
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return area
