"""Fixtures compartidas: base de datos de prueba (PostgreSQL real) y cliente HTTP.

Los tests corren sobre PostgreSQL, el mismo motor de producción (TST-C-03, prerrequisito
de la RLS de DEC-010): el esquema se crea con `alembic upgrade head`, así que también se
prueban las migraciones. La base de prueba es dedicada (por defecto, la de DATABASE_URL
con el sufijo `_test`, o TEST_DATABASE_URL si está definida) para no tocar los datos de
desarrollo. Cada test termina con un TRUNCATE de todas las tablas, así no hay estado
compartido entre tests.

El engine usa NullPool porque TestClient ejecuta la app en su propio event loop: cada
sesión abre su propia conexión en el loop que la usa, y asyncpg no comparte conexiones
entre loops.
"""
import asyncio
import os
from collections.abc import AsyncGenerator, Iterator

import asyncpg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.usuario import RolUsuario, Usuario

# Importa todos los modelos para que sus tablas queden registradas en SQLModel.metadata
# (mismo patrón que alembic/env.py); se usa para el TRUNCATE entre tests.
from app.models import area, candidato, entrevista, evaluacion, usuario, vacante  # noqa: F401

DIRECTORIO_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _url_de_prueba() -> URL:
    """URL de la base de prueba: TEST_DATABASE_URL o la de DATABASE_URL con sufijo `_test`."""
    explicita = os.environ.get("TEST_DATABASE_URL")
    if explicita:
        return make_url(explicita)
    base = make_url(settings.database_url)
    return base.set(database=f"{base.database}_test")


async def _crear_base_si_no_existe(url: URL) -> None:
    """Crea la base de prueba conectándose a la base `postgres` del mismo servidor."""
    conexion = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port or 5432,
        database="postgres",
    )
    try:
        existe = await conexion.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", url.database)
        if not existe:
            await conexion.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await conexion.close()


@pytest.fixture(scope="session")
def url_base_prueba() -> str:
    """Prepara una vez por sesión la base de prueba y le aplica las migraciones."""
    url = _url_de_prueba()
    asyncio.run(_crear_base_si_no_existe(url))

    url_texto = url.render_as_string(hide_password=False)
    # Config sin archivo .ini: así env.py no llama a fileConfig, que reconfiguraría el
    # logging de la app (y deshabilitaría sus loggers) en medio de la suite.
    config = Config()
    config.set_main_option("script_location", os.path.join(DIRECTORIO_BACKEND, "alembic"))
    config.attributes["database_url"] = url_texto
    command.upgrade(config, "head")
    return url_texto


@pytest_asyncio.fixture
async def db_engine(url_base_prueba: str) -> AsyncGenerator[AsyncEngine, None]:
    """Engine contra la base de prueba; al terminar el test vacía todas las tablas."""
    engine = create_async_engine(url_base_prueba, poolclass=NullPool)
    try:
        yield engine
    finally:
        tablas = ", ".join(f'"{tabla.name}"' for tabla in SQLModel.metadata.sorted_tables)
        async with engine.begin() as conexion:
            await conexion.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Sesión para preparar datos desde el test (corre en el event loop de pytest)."""
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def client(db_engine: AsyncEngine) -> Iterator[TestClient]:
    """TestClient con get_db sobreescrito: una sesión nueva por request contra la base de prueba."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            yield session

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
