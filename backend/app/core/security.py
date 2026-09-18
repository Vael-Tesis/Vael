"""Utilidades de seguridad: hashing de contraseñas y manejo de JWT."""
import asyncio
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.usuario import TipoToken, TokenAcceso

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*"
_CODIGO_CORTO_ALPHABET = string.ascii_uppercase + string.digits


def generate_temporary_password(length: int = 12) -> str:
    """Genera una contraseña temporal aleatoria y criptográficamente segura."""
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


async def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return await asyncio.to_thread(_pwd_context.hash, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica que una contraseña en texto plano coincida con su hash bcrypt."""
    return await asyncio.to_thread(_pwd_context.verify, plain_password, hashed_password)


def _encode_token(claims: dict[str, Any], expires_delta: timedelta) -> str:
    """Firma un JWT con los claims dados y su tiempo de expiración."""
    to_encode = claims.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def create_access_token(user_id: str, tenant_id: str, rol: str) -> str:
    """Crea el access_token de un usuario de RRHH, con tenant_id y rol como claims."""
    claims = {"sub": user_id, "tenant_id": tenant_id, "rol": rol, "type": "access"}
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return _encode_token(claims, expires_delta)


async def create_refresh_token(user_id: str, tenant_id: str) -> str:
    """Crea el refresh_token de un usuario de RRHH."""
    claims = {"sub": user_id, "tenant_id": tenant_id, "type": "refresh"}
    expires_delta = timedelta(days=settings.refresh_token_expire_days)
    return _encode_token(claims, expires_delta)


async def create_candidate_token(
    candidato_id: str,
    tenant_id: str,
    tipo: str,
    expires_hours: int = 48,
) -> str:
    """Crea el token de acceso de un candidato (tipo examen|entrevista), válido por expires_hours."""
    claims = {"sub": candidato_id, "tenant_id": tenant_id, "tipo": tipo, "type": "candidate"}
    expires_delta = timedelta(hours=expires_hours)
    return _encode_token(claims, expires_delta)


async def decode_token(token: str) -> dict[str, Any] | None:
    """Decodifica y valida un JWT; retorna sus claims o None si es inválido o expiró."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def _generar_codigo_corto() -> str:
    """Genera un código corto legible para un TokenAcceso, formato VAEL-XXXX-XXXX."""
    segmento_1 = "".join(secrets.choice(_CODIGO_CORTO_ALPHABET) for _ in range(4))
    segmento_2 = "".join(secrets.choice(_CODIGO_CORTO_ALPHABET) for _ in range(4))
    return f"VAEL-{segmento_1}-{segmento_2}"


async def emitir_token_candidato(
    candidato_id: str,
    tenant_id: str,
    tipo: TipoToken,
    db: AsyncSession,
    expires_hours: int = 48,
) -> str:
    """Genera el JWT de acceso de un candidato y persiste su TokenAcceso; retorna el JWT.

    Punto único de emisión de tokens de candidato — lo usan tanto los servicios (al
    aprobar una etapa) como los routers (al reenviar un correo de etapa manualmente).
    """
    jwt_token = await create_candidate_token(candidato_id, tenant_id, tipo.value, expires_hours)

    token_acceso = TokenAcceso(
        tenant_id=tenant_id,
        candidato_id=candidato_id,
        token=jwt_token,
        codigo_corto=_generar_codigo_corto(),
        tipo=tipo,
        expira_en=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
    )
    db.add(token_acceso)
    await db.commit()

    return jwt_token
