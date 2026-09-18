"""Endpoints de autenticación RRHH y gestión de usuarios — /api/auth/."""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_rol
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_temporary_password,
    hash_password,
    verify_password,
)
from app.models.usuario import RolUsuario, Usuario
from app.schemas.auth import (
    AccessTokenResponse,
    CambiarPasswordRequest,
    CrearUsuarioRequest,
    LoginRequest,
    MensajeResponse,
    RefreshRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.services.correos import correo_credenciales_usuario

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Autentica a un usuario RRHH por email y contraseña, y emite access_token + refresh_token."""
    statement = select(Usuario).where(Usuario.email == body.email)
    result = await db.exec(statement)
    usuario = result.first()

    if usuario is None or not usuario.activo or not await verify_password(body.password, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    access_token = await create_access_token(usuario.id, usuario.tenant_id, usuario.rol.value)
    refresh_token = await create_refresh_token(usuario.id, usuario.tenant_id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessTokenResponse:
    """Emite un nuevo access_token a partir de un refresh_token válido y vigente."""
    claims = await decode_token(body.refresh_token)
    if claims is None or claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")

    statement = select(Usuario).where(
        Usuario.id == claims.get("sub"),
        Usuario.tenant_id == claims.get("tenant_id"),
    )
    result = await db.exec(statement)
    usuario = result.first()

    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    access_token = await create_access_token(usuario.id, usuario.tenant_id, usuario.rol.value)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", response_model=MensajeResponse)
async def logout(usuario: Annotated[Usuario, Depends(get_current_user)]) -> MensajeResponse:
    """Cierra la sesión del usuario autenticado.

    NOTA: sin blacklist en Redis (no está entre las variables de la sección 12 ni en
    el stack configurado todavía), este endpoint valida el token pero no lo invalida
    server-side — seguirá siendo válido hasta su expiración natural.
    """
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
    """Crea un usuario RRHH con contraseña temporal autogenerada y la envía por correo."""
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
    await db.commit()
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
    """Desactiva a un usuario del tenant."""
    usuario = await _obtener_usuario_del_tenant(usuario_id, admin.tenant_id, db)
    usuario.activo = False
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
    """Cambia la contraseña de un usuario del tenant a un valor definido por el administrador."""
    usuario = await _obtener_usuario_del_tenant(usuario_id, admin.tenant_id, db)
    usuario.password_hash = await hash_password(body.password_nueva)
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
    """Genera una nueva contraseña temporal para el usuario y la reenvía por correo."""
    usuario = await _obtener_usuario_del_tenant(usuario_id, admin.tenant_id, db)

    password_temporal = generate_temporary_password()
    usuario.password_hash = await hash_password(password_temporal)
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)

    background_tasks.add_task(correo_credenciales_usuario, usuario, password_temporal)

    return MensajeResponse(detail="Credenciales reenviadas")
