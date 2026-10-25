"""Utilidades de seguridad: hashing de contraseñas y JWT con PyJWT (DEC-011)."""
import asyncio
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.base import utcnow
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


async def create_access_token(user_id: str, tenant_id: str, rol: str, token_version: int = 0) -> str:
    """Crea el access_token de un usuario de RRHH (15 minutos, DEC-011).

    `ver` es la versión de token del usuario: si cambia (desactivación o cambio de
    contraseña), get_current_user rechaza el token aunque no haya expirado.
    """
    claims = {"sub": user_id, "tenant_id": tenant_id, "rol": rol, "type": "access", "ver": token_version}
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return _encode_token(claims, expires_delta)


def create_refresh_token(user_id: str, tenant_id: str, sesion_id: str) -> str:
    """Crea el refresh_token de una sesión. Lleva el id de la sesión (`sid`) y el tenant, para
    buscar la sesión con la RLS fijada sin cruzar empresas (DEC-010)."""
    claims = {"sub": user_id, "tenant_id": tenant_id, "sid": sesion_id, "type": "refresh", "jti": secrets.token_hex(8)}
    expires_delta = timedelta(days=settings.refresh_token_expire_days)
    return _encode_token(claims, expires_delta)


def hash_refresh_token(token: str) -> str:
    """SHA-256 del refresh token: lo único que se guarda en `sesiones` (DEC-011)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
    """Decodifica y valida un JWT; retorna sus claims o None si es inválido o expiró.

    Solo acepta el algoritmo configurado (HS256): rechaza `alg: none` y cualquier otro.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm], options={"require": ["exp"]})
    except jwt.PyJWTError:
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
        expira_en=utcnow() + timedelta(hours=expires_hours),
    )
    db.add(token_acceso)
    await db.commit()

    return jwt_token
