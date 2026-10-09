"""Fixtures compartidas: base de datos de prueba (SQLite async) y cliente HTTP.

No hay un Postgres real disponible en este entorno (ver auditoría), así que las
pruebas de los endpoints nuevos reemplazan get_db por una sesión contra SQLite en
memoria -- el patrón estándar de FastAPI para tests sin depender de un servidor
externo. engine/tablas se recrean por test para que no haya estado compartido.
"""
from collections.abc import AsyncGenerator, Iterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.usuario import RolUsuario, Usuario

# Importa todos los modelos para que sus tablas queden registradas en SQLModel.metadata
# (si no se importan, create_all no las crea — mismo patrón que alembic/env.py).
from app.models import area, candidato, entrevista, evaluacion, usuario, vacante  # noqa: F401


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Sesión async contra una base SQLite en memoria, con el esquema recién creado."""
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield async_session
    finally:
        await async_session.close()
        await engine.dispose()


@pytest.fixture
def client(db_session: AsyncSession) -> Iterator[TestClient]:
    """TestClient con get_db sobreescrito para usar la sesión SQLite de la prueba."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


TENANT_ID = "tenant-test-0001"


async def _crear_usuario(db_session: AsyncSession, rol: RolUsuario) -> Usuario:
    """Crea (sin pasar por el endpoint) un usuario del tenant de prueba con el rol dado."""
    usuario_obj = Usuario(
        tenant_id=TENANT_ID,
        nombre="Test",
        apellidos=rol.value,
        email=f"{rol.value}@test.vael",
        password_hash="no-usado-en-estos-tests",
        rol=rol,
    )
    db_session.add(usuario_obj)
    await db_session.commit()
    await db_session.refresh(usuario_obj)
    return usuario_obj


@pytest_asyncio.fixture
async def admin_headers(db_session: AsyncSession) -> dict[str, str]:
    """Headers Authorization de un usuario ADMIN del tenant de prueba."""
    usuario_obj = await _crear_usuario(db_session, RolUsuario.ADMIN)
    token = await create_access_token(usuario_obj.id, usuario_obj.tenant_id, usuario_obj.rol.value)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def reclutador_headers(db_session: AsyncSession) -> dict[str, str]:
    """Headers Authorization de un usuario RECLUTADOR del tenant de prueba."""
    usuario_obj = await _crear_usuario(db_session, RolUsuario.RECLUTADOR)
    token = await create_access_token(usuario_obj.id, usuario_obj.tenant_id, usuario_obj.rol.value)
    return {"Authorization": f"Bearer {token}"}
