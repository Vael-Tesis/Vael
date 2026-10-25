"""Sesiones de RRHH con refresh token rotativo (DEC-011, DEV-A-02).

- Crear: guarda solo el hash del refresh token.
- Rotar: cada renovación revoca la sesión usada y crea otra que la reemplaza.
- Reutilización: si llega el refresh token de una sesión ya revocada, se revocan todas las
  sesiones activas del usuario (alguien pudo haberlo robado).
- Revocar todas: al desactivar al usuario o cambiar su contraseña, junto con token_version.

No depende de FastAPI: lanza SesionInvalida y el router responde 401.
"""
import hmac
from datetime import timedelta

from sqlalchemy import update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.security import create_refresh_token, hash_refresh_token
from app.models.base import new_id, utcnow
from app.models.usuario import Sesion, Usuario


class SesionInvalida(Exception):
    """El refresh token no corresponde a una sesión vigente."""


async def crear_sesion(usuario: Usuario, db: AsyncSession) -> str:
    """Crea una sesión para el usuario y retorna su refresh token (que no se guarda)."""
    sesion_id = new_id()
    refresh_token = create_refresh_token(usuario.id, usuario.tenant_id, sesion_id)
    db.add(
        Sesion(
            id=sesion_id,
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            token_hash=hash_refresh_token(refresh_token),
            expira_en=utcnow() + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.flush()
    return refresh_token


async def _sesion_del_token(claims: dict[str, object], refresh_token: str, db: AsyncSession) -> Sesion:
    sesion = await db.get(Sesion, claims.get("sid"))
    if (
        sesion is None
        or sesion.tenant_id != claims.get("tenant_id")
        or sesion.usuario_id != claims.get("sub")
        or not hmac.compare_digest(sesion.token_hash, hash_refresh_token(refresh_token))
    ):
        raise SesionInvalida("Refresh token inválido")
    return sesion


async def revocar_todas(usuario_id: str, tenant_id: str, db: AsyncSession) -> None:
    """Revoca todas las sesiones activas del usuario."""
    await db.exec(
        update(Sesion)
        .where(Sesion.tenant_id == tenant_id, Sesion.usuario_id == usuario_id, Sesion.revocado_en.is_(None))
        .values(revocado_en=utcnow())
    )


async def rotar(claims: dict[str, object], refresh_token: str, usuario: Usuario, db: AsyncSession) -> str:
    """Revoca la sesión del refresh token y crea otra; retorna el refresh token nuevo.

    Un refresh token ya revocado delata una reutilización: se revocan todas las sesiones.
    """
    sesion = await _sesion_del_token(claims, refresh_token, db)
    if sesion.revocado_en is not None:
        await revocar_todas(usuario.id, usuario.tenant_id, db)
        await db.commit()
        raise SesionInvalida("Refresh token reutilizado: se cerraron todas las sesiones")
    if sesion.expira_en <= utcnow():
        raise SesionInvalida("La sesión expiró")

    nuevo = await crear_sesion(usuario, db)
    nueva = (await db.exec(select(Sesion).where(Sesion.token_hash == hash_refresh_token(nuevo)))).one()
    sesion.revocado_en = utcnow()
    sesion.reemplazado_por = nueva.id
    db.add(sesion)
    await db.commit()
    return nuevo


async def cerrar(claims: dict[str, object], refresh_token: str, usuario: Usuario, db: AsyncSession) -> None:
    """Logout: revoca la sesión del refresh token si pertenece al usuario."""
    if claims.get("sub") != usuario.id:
        raise SesionInvalida("El refresh token no pertenece al usuario")
    sesion = await _sesion_del_token(claims, refresh_token, db)
    if sesion.revocado_en is None:
        sesion.revocado_en = utcnow()
        db.add(sesion)
        await db.commit()
