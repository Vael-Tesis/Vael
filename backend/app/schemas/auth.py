"""Schemas de request y response para autenticación y gestión de usuarios — /api/auth/."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.usuario import RolUsuario


class LoginRequest(BaseModel):
    """Credenciales de acceso de un usuario RRHH."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Refresh token con el que se renueva el access_token."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Par de tokens emitido al iniciar sesión y en cada renovación (el refresh rota, DEC-011)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    """Refresh token de la sesión que se cierra."""

    refresh_token: str


class UsuarioResponse(BaseModel):
    """Datos públicos de un usuario RRHH — nunca incluye password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    nombre: str
    apellidos: str
    email: EmailStr
    rol: RolUsuario
    telefono: str | None
    activo: bool
    created_at: datetime


class CrearUsuarioRequest(BaseModel):
    """Datos para crear un usuario RRHH — la contraseña se genera automáticamente y no se recibe aquí."""

    nombre: str = Field(min_length=1)
    apellidos: str = Field(min_length=1)
    email: EmailStr
    rol: RolUsuario
    telefono: str | None = None


class CambiarPasswordRequest(BaseModel):
    """Nueva contraseña asignada por un administrador a un usuario."""

    password_nueva: str = Field(min_length=8)


class MensajeResponse(BaseModel):
    """Respuesta genérica de confirmación para acciones sin cuerpo de datos."""

    detail: str
