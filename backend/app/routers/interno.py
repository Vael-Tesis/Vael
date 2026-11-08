"""Endpoints internos: las Lambdas entregan aquí sus resultados (DEC-018, DEV-C-13 · HU-23).

Nivel de permiso "Interno" (doc 06): sin JWT, solo con la firma HMAC-SHA256 de `core/interno.py`.
Excluidos del OpenAPI público. El backend fija el `tenant_id` del mensaje, persiste con la RLS
como `vael_app` (DEC-010) y verifica la idempotencia (DEC-016, punto 7): una entrega repetida
responde `aplicado: false` sin cambiar nada.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import fijar_tenant, get_db
from app.core.interno import CABECERA_FIRMA, CABECERA_MARCA, verificar_firma
from app.models.candidato import Candidato
from app.models.entrevista import EntrevistaIA
from app.schemas.interno import AplicacionResponse, ResultadoAnalisisCv, ResultadoAnalisisEntrevista
from app.services.analisis_cv import aplicar_resultado_analisis_cv
from app.services.entrevista_ia import aplicar_resultado_analisis_entrevista

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interno", tags=["interno"], include_in_schema=False)


async def cuerpo_firmado(request: Request) -> bytes:
    """Devuelve el cuerpo crudo si la firma y la marca de tiempo son válidas; si no, 401."""
    cuerpo = await request.body()
    if not verificar_firma(cuerpo, request.headers.get(CABECERA_MARCA), request.headers.get(CABECERA_FIRMA)):
        logger.warning("Entrega interna rechazada: firma ausente, inválida o vencida", extra={"path": request.url.path})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma inválida o vencida")
    return cuerpo


def _validar[T: (ResultadoAnalisisCv, ResultadoAnalisisEntrevista)](modelo: type[T], cuerpo: bytes) -> T:
    try:
        return modelo.model_validate_json(cuerpo)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors(include_url=False, include_context=False)) from exc


def _fijar_tenant_del_mensaje(request: Request, tenant_id: str) -> None:
    """Fija el tenant del mensaje antes de la primera consulta: la RLS solo deja ver sus filas."""
    fijar_tenant(tenant_id)
    request.state.tenant_id = tenant_id


@router.post("/resultados/analisis-cv", response_model=AplicacionResponse)
async def recibir_analisis_cv(
    request: Request,
    cuerpo: Annotated[bytes, Depends(cuerpo_firmado)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AplicacionResponse:
    """Aplica el resultado del análisis de un CV calculado por la Lambda."""
    resultado = _validar(ResultadoAnalisisCv, cuerpo)
    _fijar_tenant_del_mensaje(request, resultado.tenant_id)
    candidato = await db.get(Candidato, resultado.candidato_id)
    if candidato is None or candidato.tenant_id != resultado.tenant_id:
        logger.warning("Resultado de análisis de CV para un candidato inexistente en su empresa")
        return AplicacionResponse(aplicado=False)
    aplicado = await aplicar_resultado_analisis_cv(candidato, resultado.model_dump(), db)
    return AplicacionResponse(aplicado=aplicado)


@router.post("/resultados/analisis-entrevista", response_model=AplicacionResponse)
async def recibir_analisis_entrevista(
    request: Request,
    cuerpo: Annotated[bytes, Depends(cuerpo_firmado)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AplicacionResponse:
    """Aplica el resultado del análisis de una entrevista calculado por la Lambda."""
    resultado = _validar(ResultadoAnalisisEntrevista, cuerpo)
    _fijar_tenant_del_mensaje(request, resultado.tenant_id)
    entrevista = await db.get(EntrevistaIA, resultado.entrevista_id)
    if entrevista is None or entrevista.tenant_id != resultado.tenant_id:
        logger.warning("Resultado de análisis de entrevista para una entrevista inexistente en su empresa")
        return AplicacionResponse(aplicado=False)
    aplicado = await aplicar_resultado_analisis_entrevista(entrevista, resultado.model_dump(), db)
    return AplicacionResponse(aplicado=aplicado)
