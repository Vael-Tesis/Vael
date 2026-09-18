"""Endpoints públicos sin autenticación — formulario de postulación — /api/publico/."""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.models.base import new_id
from app.models.candidato import Candidato
from app.models.usuario import Empresa
from app.models.vacante import EstadoVacante, Vacante
from app.schemas.publico import PostulacionResponse, VacantePublicaResponse
from app.services.analisis_cv import analizar_cv_candidato
from app.services.aws_services import subir_archivo

router = APIRouter(prefix="/api/publico", tags=["publico"])


async def _obtener_vacante_publica_por_codigo(codigo: str, db: AsyncSession) -> Vacante:
    """Busca una vacante abierta por su código, o lanza 404 si no existe o no está abierta."""
    statement = select(Vacante).where(Vacante.codigo == codigo, Vacante.estado == EstadoVacante.ABIERTA)
    result = await db.exec(statement)
    vacante = result.first()

    if vacante is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")

    return vacante


def _construir_vacante_publica(vacante: Vacante, empresa: Empresa | None) -> VacantePublicaResponse:
    """Arma la vista pública de una vacante, ocultando datos internos y sensibles."""
    return VacantePublicaResponse(
        codigo=vacante.codigo,
        titulo=vacante.titulo,
        empresa=None if vacante.confidencial else (empresa.nombre if empresa else None),
        descripcion=vacante.descripcion,
        responsabilidades=vacante.responsabilidades,
        requisitos=vacante.requisitos,
        requisitos_deseables=vacante.requisitos_deseables,
        beneficios=vacante.beneficios,
        habilidades=vacante.habilidades,
        tecnologias=vacante.tecnologias,
        nivel_experiencia=vacante.nivel_experiencia,
        modalidad=vacante.modalidad,
        tipo_contrato=vacante.tipo_contrato,
        ciudad=vacante.ciudad,
        pais=vacante.pais,
        salario_minimo=vacante.salario_minimo if vacante.mostrar_salario else None,
        salario_maximo=vacante.salario_maximo if vacante.mostrar_salario else None,
        moneda=vacante.moneda if vacante.mostrar_salario else None,
        cantidad_posiciones=vacante.cantidad_posiciones,
        fecha_limite=vacante.fecha_limite,
    )


@router.get("/postular/{codigo}", response_model=VacantePublicaResponse)
async def obtener_vacante_publica(
    codigo: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VacantePublicaResponse:
    """Info de una vacante abierta para el formulario público de postulación.

    Accesible con el código aunque la vacante sea confidencial (el código actúa
    como el link que se comparte); solo GET /vacantes filtra las confidenciales.
    """
    vacante = await _obtener_vacante_publica_por_codigo(codigo, db)

    empresa_statement = select(Empresa).where(Empresa.tenant_id == vacante.tenant_id)
    empresa_result = await db.exec(empresa_statement)
    empresa = empresa_result.first()

    return _construir_vacante_publica(vacante, empresa)


@router.post("/postular/{codigo}/enviar", response_model=PostulacionResponse, status_code=status.HTTP_201_CREATED)
async def enviar_postulacion(
    codigo: str,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    nombre: Annotated[str, Form()],
    apellidos: Annotated[str, Form()],
    email: Annotated[EmailStr, Form()],
    cv: Annotated[UploadFile, File()],
    telefono: Annotated[str | None, Form()] = None,
    linkedin: Annotated[str | None, Form()] = None,
    github: Annotated[str | None, Form()] = None,
    portfolio: Annotated[str | None, Form()] = None,
    pretension_salarial: Annotated[float | None, Form()] = None,
) -> PostulacionResponse:
    """Recibe la postulación de un candidato (datos + CV) y dispara su análisis IA en background."""
    vacante = await _obtener_vacante_publica_por_codigo(codigo, db)

    contenido = await cv.read()
    clave = f"cvs/{vacante.tenant_id}/{vacante.id}/{new_id()}_{cv.filename}"
    cv_url = await subir_archivo(contenido, clave, cv.content_type or "application/pdf")

    candidato = Candidato(
        tenant_id=vacante.tenant_id,
        vacante_id=vacante.id,
        nombre=nombre,
        apellidos=apellidos,
        email=email,
        telefono=telefono,
        linkedin=linkedin,
        github=github,
        portfolio=portfolio,
        cv_url=cv_url,
        pretension_salarial=pretension_salarial,
    )
    db.add(candidato)
    await db.commit()
    await db.refresh(candidato)

    background_tasks.add_task(analizar_cv_candidato, candidato.id)

    return PostulacionResponse(candidato_id=candidato.id, mensaje="Postulación recibida correctamente")


@router.get("/vacantes", response_model=list[VacantePublicaResponse])
async def listar_vacantes_publicas(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[VacantePublicaResponse]:
    """Lista las vacantes públicas: abiertas y no confidenciales, de cualquier tenant."""
    statement = select(Vacante).where(Vacante.estado == EstadoVacante.ABIERTA, Vacante.confidencial.is_(False))
    result = await db.exec(statement)
    vacantes = list(result.all())

    tenant_ids = {v.tenant_id for v in vacantes}
    empresas_por_tenant: dict[str, Empresa] = {}
    if tenant_ids:
        empresas_statement = select(Empresa).where(Empresa.tenant_id.in_(tenant_ids))
        empresas_result = await db.exec(empresas_statement)
        empresas_por_tenant = {e.tenant_id: e for e in empresas_result.all()}

    return [_construir_vacante_publica(v, empresas_por_tenant.get(v.tenant_id)) for v in vacantes]
