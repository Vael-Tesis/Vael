"""Endpoints de gestión de plantillas de evaluación y sus dimensiones — /api/plantillas/."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_rol
from app.models.entrevista import DimensionEvaluacion, PlantillaEvaluacion
from app.models.usuario import RolUsuario, Usuario
from app.schemas.plantilla import (
    DimensionCreateRequest,
    DimensionResponse,
    DimensionUpdateRequest,
    MensajeResponse,
    PlantillaCreateRequest,
    PlantillaDetalleResponse,
    PlantillaResponse,
    PlantillaUpdateRequest,
)

router = APIRouter(prefix="/api/plantillas", tags=["plantillas"])

_ADMIN_O_GERENTE = (RolUsuario.ADMIN, RolUsuario.GERENTE)


async def _obtener_plantilla_del_tenant(plantilla_id: str, tenant_id: str, db: AsyncSession) -> PlantillaEvaluacion:
    """Busca una plantilla por id dentro del tenant actual, o lanza 404 si no existe."""
    statement = select(PlantillaEvaluacion).where(
        PlantillaEvaluacion.id == plantilla_id, PlantillaEvaluacion.tenant_id == tenant_id
    )
    result = await db.exec(statement)
    plantilla = result.first()

    if plantilla is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")

    return plantilla


async def _listar_dimensiones(plantilla_id: str, db: AsyncSession) -> list[DimensionEvaluacion]:
    """Lista las dimensiones de una plantilla."""
    statement = select(DimensionEvaluacion).where(DimensionEvaluacion.plantilla_id == plantilla_id)
    result = await db.exec(statement)
    return list(result.all())


async def _obtener_dimension_del_tenant(
    plantilla_id: str, dimension_id: str, tenant_id: str, db: AsyncSession
) -> DimensionEvaluacion:
    """Busca una dimensión por id dentro de la plantilla y tenant actuales, o lanza 404 si no existe."""
    statement = select(DimensionEvaluacion).where(
        DimensionEvaluacion.id == dimension_id,
        DimensionEvaluacion.plantilla_id == plantilla_id,
        DimensionEvaluacion.tenant_id == tenant_id,
    )
    result = await db.exec(statement)
    dimension = result.first()

    if dimension is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dimensión no encontrada")

    return dimension


@router.get("", response_model=list[PlantillaResponse])
async def listar_plantillas(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    activa: bool | None = None,
) -> list[PlantillaEvaluacion]:
    """Lista las plantillas de evaluación del tenant, con filtro opcional por estado activa."""
    statement = select(PlantillaEvaluacion).where(PlantillaEvaluacion.tenant_id == actor.tenant_id)

    if activa is not None:
        statement = statement.where(PlantillaEvaluacion.activa == activa)

    result = await db.exec(statement)
    return list(result.all())


@router.post("/", response_model=PlantillaDetalleResponse, status_code=status.HTTP_201_CREATED)
async def crear_plantilla(
    body: PlantillaCreateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlantillaDetalleResponse:
    """Crea una plantilla de evaluación junto con sus dimensiones iniciales."""
    plantilla = PlantillaEvaluacion(
        tenant_id=actor.tenant_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        activa=body.activa,
    )
    db.add(plantilla)
    await db.commit()
    await db.refresh(plantilla)

    dimensiones = [
        DimensionEvaluacion(tenant_id=actor.tenant_id, plantilla_id=plantilla.id, **dim.model_dump())
        for dim in body.dimensiones
    ]
    for dimension in dimensiones:
        db.add(dimension)
    if dimensiones:
        await db.commit()
        for dimension in dimensiones:
            await db.refresh(dimension)

    return PlantillaDetalleResponse(
        **PlantillaResponse.model_validate(plantilla).model_dump(),
        dimensiones=[DimensionResponse.model_validate(d) for d in dimensiones],
    )


@router.get("/{plantilla_id}", response_model=PlantillaDetalleResponse)
async def obtener_plantilla(
    plantilla_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlantillaDetalleResponse:
    """Retorna el detalle de una plantilla con sus dimensiones."""
    plantilla = await _obtener_plantilla_del_tenant(plantilla_id, actor.tenant_id, db)
    dimensiones = await _listar_dimensiones(plantilla.id, db)

    return PlantillaDetalleResponse(
        **PlantillaResponse.model_validate(plantilla).model_dump(),
        dimensiones=[DimensionResponse.model_validate(d) for d in dimensiones],
    )


@router.put("/{plantilla_id}", response_model=PlantillaDetalleResponse)
async def editar_plantilla(
    plantilla_id: str,
    body: PlantillaUpdateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlantillaDetalleResponse:
    """Edita los campos provistos de una plantilla (actualización parcial, sin tocar dimensiones)."""
    plantilla = await _obtener_plantilla_del_tenant(plantilla_id, actor.tenant_id, db)

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(plantilla, campo, valor)

    db.add(plantilla)
    await db.commit()
    await db.refresh(plantilla)

    dimensiones = await _listar_dimensiones(plantilla.id, db)
    return PlantillaDetalleResponse(
        **PlantillaResponse.model_validate(plantilla).model_dump(),
        dimensiones=[DimensionResponse.model_validate(d) for d in dimensiones],
    )


@router.post(
    "/{plantilla_id}/dimensiones", response_model=DimensionResponse, status_code=status.HTTP_201_CREATED
)
async def agregar_dimension(
    plantilla_id: str,
    body: DimensionCreateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DimensionEvaluacion:
    """Agrega una dimensión a evaluar dentro de una plantilla."""
    plantilla = await _obtener_plantilla_del_tenant(plantilla_id, actor.tenant_id, db)

    dimension = DimensionEvaluacion(tenant_id=actor.tenant_id, plantilla_id=plantilla.id, **body.model_dump())
    db.add(dimension)
    await db.commit()
    await db.refresh(dimension)
    return dimension


@router.put("/{plantilla_id}/dimensiones/{dimension_id}", response_model=DimensionResponse)
async def editar_dimension(
    plantilla_id: str,
    dimension_id: str,
    body: DimensionUpdateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DimensionEvaluacion:
    """Edita los campos provistos de una dimensión (actualización parcial)."""
    dimension = await _obtener_dimension_del_tenant(plantilla_id, dimension_id, actor.tenant_id, db)

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(dimension, campo, valor)

    db.add(dimension)
    await db.commit()
    await db.refresh(dimension)
    return dimension


@router.delete("/{plantilla_id}/dimensiones/{dimension_id}", response_model=MensajeResponse)
async def eliminar_dimension(
    plantilla_id: str,
    dimension_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_ADMIN_O_GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Elimina una dimensión de una plantilla."""
    dimension = await _obtener_dimension_del_tenant(plantilla_id, dimension_id, actor.tenant_id, db)

    await db.delete(dimension)
    await db.commit()
    return MensajeResponse(detail="Dimensión eliminada")
