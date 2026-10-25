"""Endpoints de autenticación RRHH y gestión de usuarios — /api/auth/."""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import fijar_tenant, get_db, get_system_db
from app.core.dependencies import get_current_user, require_rol
from app.core.security import (
    create_access_token,
    decode_token,
    generate_temporary_password,
    hash_password,
    verify_password,
)
from app.models.base import utcnow
from app.models.usuario import RolUsuario, Usuario
from app.schemas.auth import (
    CambiarPasswordRequest,
    CrearUsuarioRequest,
    LoginRequest,
    LogoutRequest,
    MensajeResponse,
    RefreshRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.services import sesiones
from app.services.correos import correo_credenciales_usuario

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _revocar_acceso(usuario: Usuario, db: AsyncSession) -> None:
    """Sube token_version (rechaza los access tokens vigentes) y revoca todas sus sesiones."""
    usuario.token_version += 1
    usuario.updated_at = utcnow()
    await sesiones.revocar_todas(usuario.id, usuario.tenant_id, db)


async def _obtener_usuario_del_tenant(usuario_id: str, tenant_id: str, db: AsyncSession) -> Usuario:
    """Busca un usuario por id dentro del tenant actual, o lanza 404 si no existe."""
    statement = select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    result = await db.exec(statement)
    usuario = result.first()

    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    return usuario


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_system_db)],
) -> TokenResponse:
    """Autentica a un usuario RRHH por email y contraseña, y emite access_token + refresh_token.

    Usa la sesión del sistema (lista cerrada de DEC-010): busca por email antes de
    conocer la empresa del usuario. Crea la fila de la sesión con el hash del refresh token
    (DEC-011). Credenciales incorrectas: 401; usuario inactivo: 403.
    """
    statement = select(Usuario).where(Usuario.email == body.email)
    result = await db.exec(statement)
    usuario = result.first()

    if usuario is None or not await verify_password(body.password, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    # Solo con la contraseña correcta se revela que la cuenta está inactiva (CA-01)
    if not usuario.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El usuario está inactivo")

    refresh_token = await sesiones.crear_sesion(usuario, db)
    await db.commit()
    access_token = await create_access_token(usuario.id, usuario.tenant_id, usuario.rol.value, usuario.token_version)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Renueva la sesión: revoca el refresh token usado y emite un par nuevo (rotación, DEC-011).

    Si el refresh token ya estaba revocado, revoca todas las sesiones del usuario (401).
    """
    claims = await decode_token(body.refresh_token)
    if claims is None or claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")
    tenant_id = claims.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")
    # El refresh no pasa por _get_token_claims: fija aquí el tenant para la RLS (DEC-010).
    fijar_tenant(tenant_id)

    statement = select(Usuario).where(
        Usuario.id == claims.get("sub"),
        Usuario.tenant_id == claims.get("tenant_id"),
    )
    result = await db.exec(statement)
    usuario = result.first()

    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    try:
        refresh_token = await sesiones.rotar(claims, body.refresh_token, usuario, db)
    except sesiones.SesionInvalida as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error

    access_token = await create_access_token(usuario.id, usuario.tenant_id, usuario.rol.value, usuario.token_version)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=MensajeResponse)
async def logout(
    body: LogoutRequest,
    usuario: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Cierra la sesión: revoca su refresh token, que deja de servir para renovar (DEC-011).

    El access token vigente expira solo, en 15 minutos como máximo (trade-off de DEC-011).
    """
    claims = await decode_token(body.refresh_token)
    if claims is None or claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")
    try:
        await sesiones.cerrar(claims, body.refresh_token, usuario, db)
    except sesiones.SesionInvalida as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    return MensajeResponse(detail="Sesión cerrada")


@router.get("/perfil", response_model=UsuarioResponse)
async def perfil(usuario: Annotated[Usuario, Depends(get_current_user)]) -> Usuario:
    """Retorna los datos del usuario RRHH autenticado."""
    return usuario


@router.post("/usuarios/crear", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    body: CrearUsuarioRequest,
    background_tasks: BackgroundTasks,
    admin: Annotated[Usuario, Depends(require_rol(RolUsuario.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Crea un usuario RRHH con contraseña temporal autogenerada y la envía por correo.

    El email es único en toda la plataforma (el login lo busca sin conocer la empresa).
    Con RLS, la consulta previa solo ve los usuarios del tenant; un email de otra empresa
    lo detiene el índice único de la base al hacer commit.
    """
    statement = select(Usuario).where(Usuario.email == body.email)
    result = await db.exec(statement)
    if result.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    password_temporal = generate_temporary_password()

    usuario = Usuario(
        tenant_id=admin.tenant_id,
        nombre=body.nombre,
        apellidos=body.apellidos,
        email=body.email,
        password_hash=await hash_password(password_temporal),
        rol=body.rol,
        telefono=body.telefono,
    )
    db.add(usuario)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado") from exc
    await db.refresh(usuario)

    background_tasks.add_task(correo_credenciales_usuario, usuario, password_temporal)

    return usuario


@router.get("/usuarios", response_model=list[UsuarioResponse])
async def listar_usuarios(
    actor: Annotated[Usuario, Depends(require_rol(RolUsuario.ADMIN, RolUsuario.GERENTE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Usuario]:
    """Lista los usuarios RRHH del tenant actual."""
    statement = select(Usuario).where(Usuario.tenant_id == actor.tenant_id)
    result = await db.exec(statement)
    return list(result.all())


@router.put("/usuarios/{usuario_id}/activar", response_model=UsuarioResponse)
async def activar_usuario(
    usuario_id: str,
    admin: Annotated[Usuario, Depends(require_rol(RolUsuario.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Activa a un usuario del tenant."""
    usuario = await _obtener_usuario_del_tenant(usuario_id, admin.tenant_id, db)
    usuario.activo = True
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.put("/usuarios/{usuario_id}/desactivar", response_model=UsuarioResponse)
async def desactivar_usuario(
    usuario_id: str,
    admin: Annotated[Usuario, Depends(require_rol(RolUsuario.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Desactiva a un usuario del tenant e invalida al instante sus tokens y sesiones (DEC-011)."""
    usuario = await _obtener_usuario_del_tenant(usuario_id, admin.tenant_id, db)
    usuario.activo = False
    await _revocar_acceso(usuario, db)
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.put("/usuarios/{usuario_id}/cambiar-password", response_model=UsuarioResponse)
async def cambiar_password(
    usuario_id: str,
    body: CambiarPasswordRequest,
    admin: Annotated[Usuario, Depends(require_rol(RolUsuario.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Cambia la contraseña de un usuario e invalida sus tokens y sesiones (DEC-011)."""
    usuario = await _obtener_usuario_del_tenant(usuario_id, admin.tenant_id, db)
    usuario.password_hash = await hash_password(body.password_nueva)
    await _revocar_acceso(usuario, db)
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.post("/usuarios/{usuario_id}/reenviar-credenciales", response_model=MensajeResponse)
async def reenviar_credenciales(
    usuario_id: str,
    background_tasks: BackgroundTasks,
    admin: Annotated[Usuario, Depends(require_rol(RolUsuario.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MensajeResponse:
    """Genera una nueva contraseña temporal para el usuario y la reenvía por correo.

    Es un cambio de contraseña: invalida los tokens y las sesiones anteriores (DEC-011).
    """
    usuario = await _obtener_usuario_del_tenant(usuario_id, admin.tenant_id, db)

    password_temporal = generate_temporary_password()
    usuario.password_hash = await hash_password(password_temporal)
    await _revocar_acceso(usuario, db)
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)

    background_tasks.add_task(correo_credenciales_usuario, usuario, password_temporal)

    return MensajeResponse(detail="Credenciales reenviadas")
