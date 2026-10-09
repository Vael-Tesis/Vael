"""Endpoints de gestión de vacantes — /api/vacantes/."""
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Annotated
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_rol
from app.models.area import Area
from app.models.base import utcnow
from app.models.usuario import Empresa, RolUsuario, Usuario
from app.models.vacante import EstadoVacante, PrioridadVacante, TipoContrato, Vacante
from app.schemas.vacante import (
    TextosMarketingResponse,
    VacanteCreateRequest,
    VacanteResponse,
    VacanteUpdateRequest,
)
from app.services.vacante_ia import generar_textos_marketing

router = APIRouter(prefix="/api/vacantes", tags=["vacantes"])

_RECLUTADOR_O_SUPERIOR = (RolUsuario.ADMIN, RolUsuario.GERENTE, RolUsuario.RECLUTADOR)

_JOBTYPE_POR_CONTRATO = {
    TipoContrato.INDEFINIDO: "fulltime",
    TipoContrato.PLAZO_FIJO: "fulltime",
    TipoContrato.PRACTICAS: "internship",
    TipoContrato.FREELANCE: "contract",
    TipoContrato.PART_TIME: "parttime",
}


async def _obtener_vacante_del_tenant(vacante_id: str, tenant_id: str, db: AsyncSession) -> Vacante:
    """Busca una vacante por id dentro del tenant actual, o lanza 404 si no existe."""
    statement = select(Vacante).where(Vacante.id == vacante_id, Vacante.tenant_id == tenant_id)
    result = await db.exec(statement)
    vacante = result.first()

    if vacante is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")

    return vacante


async def _generar_codigo_vacante(area_id: str, tenant_id: str, db: AsyncSession) -> str:
    """Genera el código de una vacante con el formato {CODIGO_AREA}-{AÑO}-{NNN}."""
    area_statement = select(Area).where(Area.id == area_id, Area.tenant_id == tenant_id)
    area_result = await db.exec(area_statement)
    area = area_result.first()

    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área no encontrada")

    anio = datetime.now(timezone.utc).year
    prefijo = f"{area.codigo_corto}-{anio}-"

    statement = select(Vacante).where(Vacante.tenant_id == tenant_id, Vacante.codigo.like(f"{prefijo}%"))
    result = await db.exec(statement)

    numeros = [
        int(sufijo) for v in result.all() if (sufijo := v.codigo.rsplit("-", 1)[-1]).isdigit()
    ]
    siguiente = max(numeros, default=0) + 1

    return f"{prefijo}{siguiente:03d}"


def _construir_feed_xml(vacante: Vacante, empresa: Empresa | None) -> bytes:
    """Arma el feed XML de una vacante en el formato esperado por bolsas de empleo (Indeed)."""
    source = Element("source")
    SubElement(source, "publisher").text = "VAEL"
    SubElement(source, "publisherurl").text = settings.frontend_url

    job = SubElement(source, "job")
    SubElement(job, "title").text = vacante.titulo
    SubElement(job, "date").text = format_datetime(vacante.created_at)
    SubElement(job, "referencenumber").text = vacante.codigo
    SubElement(job, "url").text = f"{settings.frontend_url}/postular/{vacante.codigo}"
    SubElement(job, "company").text = empresa.nombre if empresa else "VAEL"
    SubElement(job, "city").text = vacante.ciudad or ""
    SubElement(job, "country").text = vacante.pais or ""
    SubElement(job, "description").text = vacante.descripcion or ""
    if vacante.tipo_contrato is not None:
        SubElement(job, "jobtype").text = _JOBTYPE_POR_CONTRATO.get(vacante.tipo_contrato, "fulltime")

    return tostring(source, encoding="utf-8", xml_declaration=True)


@router.get("", response_model=list[VacanteResponse])
async def listar_vacantes(
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    estado: EstadoVacante | None = None,
    area_id: str | None = None,
    prioridad: PrioridadVacante | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Vacante]:
    """Lista las vacantes del tenant, con filtros opcionales por estado, área y prioridad."""
    statement = select(Vacante).where(Vacante.tenant_id == actor.tenant_id)

    if estado is not None:
        statement = statement.where(Vacante.estado == estado)
    if area_id is not None:
        statement = statement.where(Vacante.area_id == area_id)
    if prioridad is not None:
        statement = statement.where(Vacante.prioridad == prioridad)

    statement = statement.offset(skip).limit(limit)

    result = await db.exec(statement)
    return list(result.all())


@router.post("/", response_model=VacanteResponse, status_code=status.HTTP_201_CREATED)
async def crear_vacante(
    body: VacanteCreateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Vacante:
    """Crea una vacante en estado borrador (wizard de 4 pasos); el código se genera automáticamente."""
    codigo = await _generar_codigo_vacante(body.area_id, actor.tenant_id, db)

    vacante = Vacante(
        tenant_id=actor.tenant_id,
        area_id=body.area_id,
        codigo=codigo,
        **body.model_dump(exclude={"area_id"}),
    )
    db.add(vacante)
    await db.commit()
    await db.refresh(vacante)
    return vacante


@router.get("/{vacante_id}", response_model=VacanteResponse)
async def obtener_vacante(
    vacante_id: str,
    actor: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Vacante:
    """Retorna el detalle completo de una vacante."""
    return await _obtener_vacante_del_tenant(vacante_id, actor.tenant_id, db)


@router.put("/{vacante_id}", response_model=VacanteResponse)
async def editar_vacante(
    vacante_id: str,
    body: VacanteUpdateRequest,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Vacante:
    """Edita los campos provistos de una vacante (actualización parcial)."""
    vacante = await _obtener_vacante_del_tenant(vacante_id, actor.tenant_id, db)

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(vacante, campo, valor)

    vacante.updated_at = utcnow()
    db.add(vacante)
    await db.commit()
    await db.refresh(vacante)
    return vacante


@router.post("/{vacante_id}/publicar", response_model=VacanteResponse)
async def publicar_vacante(
    vacante_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Vacante:
    """Cambia el estado de la vacante a abierta."""
    vacante = await _obtener_vacante_del_tenant(vacante_id, actor.tenant_id, db)
    vacante.estado = EstadoVacante.ABIERTA
    vacante.updated_at = utcnow()
    db.add(vacante)
    await db.commit()
    await db.refresh(vacante)
    return vacante


@router.post("/{vacante_id}/pausar", response_model=VacanteResponse)
async def pausar_vacante(
    vacante_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Vacante:
    """Pausa la vacante."""
    vacante = await _obtener_vacante_del_tenant(vacante_id, actor.tenant_id, db)
    vacante.estado = EstadoVacante.PAUSADA
    vacante.updated_at = utcnow()
    db.add(vacante)
    await db.commit()
    await db.refresh(vacante)
    return vacante


@router.post("/{vacante_id}/cerrar", response_model=VacanteResponse)
async def cerrar_vacante(
    vacante_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Vacante:
    """Cierra la vacante."""
    vacante = await _obtener_vacante_del_tenant(vacante_id, actor.tenant_id, db)
    vacante.estado = EstadoVacante.CERRADA
    vacante.updated_at = utcnow()
    db.add(vacante)
    await db.commit()
    await db.refresh(vacante)
    return vacante


@router.post("/{vacante_id}/duplicar", response_model=VacanteResponse, status_code=status.HTTP_201_CREATED)
async def duplicar_vacante(
    vacante_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Vacante:
    """Crea una copia en borrador de la vacante, con un código nuevo generado para la misma área."""
    original = await _obtener_vacante_del_tenant(vacante_id, actor.tenant_id, db)
    codigo = await _generar_codigo_vacante(original.area_id, actor.tenant_id, db)

    copia = Vacante(
        tenant_id=actor.tenant_id,
        area_id=original.area_id,
        codigo=codigo,
        titulo=f"{original.titulo} (copia)",
        descripcion=original.descripcion,
        responsabilidades=original.responsabilidades,
        requisitos=original.requisitos,
        requisitos_deseables=original.requisitos_deseables,
        beneficios=original.beneficios,
        habilidades=list(original.habilidades),
        tecnologias=list(original.tecnologias),
        nivel_experiencia=original.nivel_experiencia,
        anios_experiencia=original.anios_experiencia,
        modalidad=original.modalidad,
        tipo_contrato=original.tipo_contrato,
        ciudad=original.ciudad,
        pais=original.pais,
        salario_minimo=original.salario_minimo,
        salario_maximo=original.salario_maximo,
        moneda=original.moneda,
        mostrar_salario=original.mostrar_salario,
        confidencial=original.confidencial,
        estado=EstadoVacante.BORRADOR,
        prioridad=original.prioridad,
        fecha_limite=original.fecha_limite,
        jefe_directo=original.jefe_directo,
        solicitante=original.solicitante,
        cantidad_posiciones=original.cantidad_posiciones,
        score_cv_minimo=original.score_cv_minimo,
        nota_minima_examen=original.nota_minima_examen,
        top_candidatos_finalistas=original.top_candidatos_finalistas,
        instruccion_ia_extra=original.instruccion_ia_extra,
    )
    db.add(copia)
    await db.commit()
    await db.refresh(copia)
    return copia


@router.post("/{vacante_id}/generar-textos", response_model=TextosMarketingResponse)
async def generar_textos_vacante(
    vacante_id: str,
    actor: Annotated[Usuario, Depends(require_rol(*_RECLUTADOR_O_SUPERIOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TextosMarketingResponse:
    """Genera, con Gemini, textos de difusión de la vacante para distintos canales (LinkedIn, WhatsApp, etc.)."""
    vacante = await _obtener_vacante_del_tenant(vacante_id, actor.tenant_id, db)
    textos = await generar_textos_marketing(vacante)
    return TextosMarketingResponse(textos=textos)


@router.get("/{vacante_id}/feed-xml")
async def feed_xml_vacante(
    vacante_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Feed XML de la vacante para bolsas de empleo externas (Indeed) — público, sin autenticación."""
    statement = select(Vacante).where(Vacante.id == vacante_id)
    result = await db.exec(statement)
    vacante = result.first()

    if vacante is None or vacante.estado != EstadoVacante.ABIERTA or vacante.confidencial:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")

    empresa_statement = select(Empresa).where(Empresa.tenant_id == vacante.tenant_id)
    empresa_result = await db.exec(empresa_statement)
    empresa = empresa_result.first()

    xml_bytes = _construir_feed_xml(vacante, empresa)
    return Response(content=xml_bytes, media_type="application/xml")
