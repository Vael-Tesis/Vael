"""Endpoints de gestión de áreas/departamentos — /api/areas/."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_rol
from app.models.area import Area
from app.models.base import utcnow
from app.models.usuario import RolUsuario, Usuario
from app.models.vacante import Vacante
from app.schemas.area import AreaCreateRequest, AreaResponse, AreaUpdateRequest, MensajeResponse

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


async def _exigir_codigo_libre(codigo_corto: str, tenant_id: str, db: AsyncSession, excepto_id: str | None = None) -> None:
    """El código corto es único dentro de la empresa (CA-05); se compara sin distinguir mayúsculas."""
    statement = select(Area).where(Area.tenant_id == tenant_id, func.upper(Area.codigo_corto) == codigo_corto.upper())
    if excepto_id is not None:
        statement = statement.where(Area.id != excepto_id)
    if (await db.exec(statement)).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Ya existe un área con el código {codigo_corto}")


async def _cambiar_activa(area_id: str, activa: bool, actor: Usuario, db: AsyncSession) -> Area:
    area = await _obtener_area_del_tenant(area_id, actor.tenant_id, db)
    area.activa = activa
    area.updated_at = utcnow()
    db.add(area)
    await db.commit()
    await db.refresh(area)
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
    """Crea un área o departamento para el tenant actual. 409 si el código corto ya existe."""
    await _exigir_codigo_libre(body.codigo_corto, actor.tenant_id, db)
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
    """Edita los campos provistos de un área (actualización parcial). 409 si el código corto ya existe."""
    area = await _obtener_area_del_tenant(area_id, actor.tenant_id, db)
    if body.codigo_corto is not None:
        await _exigir_codigo_libre(body.codigo_corto, actor.tenant_id, db, excepto_id=area.id)

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(area, campo, valor)

    area.updated_at = utcnow()
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return area


@router.post("/{area_id}/activar", response_model=AreaResponse)
async def activar_area(
    area_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Area:
    """Activa un área (HU-05)."""
    return await _cambiar_activa(area_id, True, actor, db)


@router.post("/{area_id}/desactivar", response_model=AreaResponse)
async def desactivar_area(
    area_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Area:
    """Desactiva un área: deja de ofrecerse para vacantes nuevas, sin tocar las existentes (HU-05)."""
    return await _cambiar_activa(area_id, False, actor, db)


@router.delete("/{area_id}", response_model=MensajeResponse)
async def eliminar_area(
    area_id: str,
    actor: Annotated[Usuario, Depends(require_rol(RolUsuario.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Elimina un área solo si no tiene vacantes; si las tiene, 409 (CA-05): se desactiva en su lugar."""
    area = await _obtener_area_del_tenant(area_id, actor.tenant_id, db)
    con_vacantes = select(Vacante.id).where(Vacante.tenant_id == actor.tenant_id, Vacante.area_id == area.id)
    if (await db.exec(con_vacantes)).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El área tiene vacantes y no se puede eliminar; desactívala en su lugar",
        )
    await db.delete(area)
    await db.commit()
    return MensajeResponse(detail="Área eliminada")
