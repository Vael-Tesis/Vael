"""Fixtures compartidas: base de datos de prueba (PostgreSQL real) y cliente HTTP.

Los tests corren sobre PostgreSQL, el mismo motor de producción (TST-C-03), y con los
mismos roles que producción (DEC-010): la app como `vael_app` (sujeta a la RLS), la lista
cerrada como `vael_system` y las migraciones como `vael_owner`. Si los tests se
conectaran como superusuario, la RLS no se aplicaría y no se estaría probando nada.

La base de prueba es dedicada (la de DATABASE_OWNER_URL con el sufijo `_test`) para no
tocar los datos de desarrollo. Una vez por sesión se crea, se crean los roles con
app.scripts.crear_roles (como DATABASE_ADMIN_URL) y se migra con `alembic upgrade head`.
Cada test termina con un TRUNCATE de todas las tablas, ejecutado por `vael_owner`.

Los engines usan NullPool porque TestClient ejecuta la app en su propio event loop: cada
sesión abre su propia conexión en el loop que la usa, y asyncpg no comparte conexiones
entre loops.
"""
import asyncio
import os
from collections.abc import AsyncGenerator, Iterator
from dataclasses import dataclass

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
from app.core.database import CLAVE_TENANT, get_db, get_system_db
from app.core.security import create_access_token
from app.main import app
from app.models.usuario import RolUsuario, Usuario
from app.scripts.crear_roles import ROL_APP, ROL_OWNER, ROL_SYSTEM, Credencial, crear_roles, url_admin

# Importa todos los modelos para que sus tablas queden registradas en SQLModel.metadata
# (mismo patrón que alembic/env.py); se usa para el TRUNCATE entre tests.
from app.models import area, candidato, entrevista, evaluacion, usuario, vacante  # noqa: F401

DIRECTORIO_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TENANT_ID = "tenant-test-0001"
TENANT_ID_OTRO = "tenant-test-0002"


@dataclass(frozen=True)
class UrlsPrueba:
    """URLs de la base de prueba, una por rol."""

    app: str
    system: str
    owner: str


def _en_base(url_texto: str, base: str) -> URL:
    return make_url(url_texto).set(database=base)


def _texto(url: URL) -> str:
    return url.render_as_string(hide_password=False)


async def _crear_base_si_no_existe(admin: URL, base: str) -> None:
    """Crea la base de prueba conectándose como administrador a la base `postgres`."""
    conexion = await asyncpg.connect(
        user=admin.username,
        password=admin.password,
        host=admin.host,
        port=admin.port or 5432,
        database="postgres",
    )
    try:
        existe = await conexion.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", base)
        if not existe:
            await conexion.execute(f'CREATE DATABASE "{base}"')
    finally:
        await conexion.close()


@pytest.fixture(scope="session")
def urls_prueba() -> UrlsPrueba:
    """Prepara una vez por sesión la base de prueba: la crea, crea los roles y la migra."""
    base = f"{make_url(settings.database_owner_url).database}_test"
    app_url = _en_base(settings.database_url, base)
    system_url = _en_base(settings.database_system_url, base)
    owner_url = _en_base(settings.database_owner_url, base)

    admin = url_admin()
    asyncio.run(_crear_base_si_no_existe(admin, base))
    asyncio.run(
        crear_roles(
            admin,
            base,
            app=Credencial(ROL_APP, app_url.password or ""),
            system=Credencial(ROL_SYSTEM, system_url.password or ""),
            owner=Credencial(ROL_OWNER, owner_url.password or ""),
        )
    )

    # Config sin archivo .ini: así env.py no llama a fileConfig, que reconfiguraría el
    # logging de la app (y deshabilitaría sus loggers) en medio de la suite.
    config = Config()
    config.set_main_option("script_location", os.path.join(DIRECTORIO_BACKEND, "alembic"))
    config.attributes["database_url"] = _texto(owner_url)
    command.upgrade(config, "head")

    return UrlsPrueba(app=_texto(app_url), system=_texto(system_url), owner=_texto(owner_url))


@pytest_asyncio.fixture
async def db_engine(urls_prueba: UrlsPrueba) -> AsyncGenerator[AsyncEngine, None]:
    """Engine `vael_app` contra la base de prueba; al terminar el test vacía todas las tablas."""
    engine = create_async_engine(urls_prueba.app, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()
        owner = create_async_engine(urls_prueba.owner, poolclass=NullPool)
        tablas = ", ".join(f'"{tabla.name}"' for tabla in SQLModel.metadata.sorted_tables)
        async with owner.begin() as conexion:
            await conexion.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
        await owner.dispose()


@pytest_asyncio.fixture
async def system_engine(urls_prueba: UrlsPrueba) -> AsyncGenerator[AsyncEngine, None]:
    """Engine `vael_system` (BYPASSRLS) contra la base de prueba."""
    engine = create_async_engine(urls_prueba.system, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Sesión `vael_app` con el tenant de prueba fijado, para preparar datos desde el test."""
    async with AsyncSession(db_engine, expire_on_commit=False, info={CLAVE_TENANT: TENANT_ID}) as session:
        yield session


@pytest.fixture
def client(db_engine: AsyncEngine, system_engine: AsyncEngine) -> Iterator[TestClient]:
    """TestClient con las sesiones sobreescritas: una sesión nueva por request en la base de prueba.

    La sesión normal no trae tenant: lo fija la app a partir del JWT, igual que en producción.
    """

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            yield session

    async def _override_get_system_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSession(system_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_system_db] = _override_get_system_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_system_db, None)


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
