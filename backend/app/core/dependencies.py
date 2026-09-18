"""Dependencias de FastAPI: sesión de BD, usuario actual, tenant y validación de rol."""
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.candidato import Candidato
from app.models.usuario import Usuario

_bearer_scheme = HTTPBearer(auto_error=True)


async def _get_token_claims(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> dict[str, Any]:
    """Decodifica el JWT del header Authorization (vía core/security.py) y retorna sus claims."""
    claims = await decode_token(credentials.credentials)
    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    return claims


async def get_current_user(
    claims: Annotated[dict[str, Any], Depends(_get_token_claims)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Extrae y valida el usuario RRHH autenticado a partir del access_token."""
    if claims.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no es un access_token de usuario",
        )

    statement = select(Usuario).where(
        Usuario.id == claims.get("sub"),
        Usuario.tenant_id == claims.get("tenant_id"),
    )
    result = await db.exec(statement)
    usuario = result.first()

    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    return usuario


async def get_tenant(claims: Annotated[dict[str, Any], Depends(_get_token_claims)]) -> str:
    """Extrae el tenant_id del JWT — usado para filtrar todos los queries por tenant."""
    tenant_id = claims.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El token no contiene tenant_id")
    return tenant_id


async def get_current_candidate(
    claims: Annotated[dict[str, Any], Depends(_get_token_claims)],
) -> dict[str, Any]:
    """Valida el token de acceso de un candidato (examen o entrevista) y retorna sus claims."""
    if claims.get("type") != "candidate":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no es un token de candidato",
        )
    return claims


async def get_current_candidato(
    claims: Annotated[dict[str, Any], Depends(get_current_candidate)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Candidato:
    """Resuelve el registro completo del Candidato dueño del token (claims: sub, tenant_id).

    Complementa a get_current_candidate: úsala cuando el endpoint necesita el candidato
    de BD, no solo sus claims (para el chequeo de claims["tipo"], sigue haciendo falta
    inyectar get_current_candidate por separado — FastAPI cachea la dependencia, así que
    el JWT no se decodifica dos veces).
    """
    statement = select(Candidato).where(
        Candidato.id == claims.get("sub"),
        Candidato.tenant_id == claims.get("tenant_id"),
    )
    result = await db.exec(statement)
    candidato = result.first()

    if candidato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidato no encontrado")

    return candidato


def require_rol(*roles: str) -> Callable[..., Any]:
    """Factory de dependencia que exige que el usuario autenticado tenga uno de los roles dados."""

    async def _verificar_rol(usuario: Annotated[Usuario, Depends(get_current_user)]) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción",
            )
        return usuario

    return _verificar_rol
