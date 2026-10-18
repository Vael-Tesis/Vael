"""Configuración de Alembic — entorno async para las migraciones de VAEL."""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context
from app.core.config import settings

# Importa todos los modelos existentes para que sus tablas se registren en SQLModel.metadata
from app.models import area, candidato, entrevista, evaluacion, usuario, vacante  # noqa: F401

# Objeto de configuración de Alembic (lee alembic.ini)
config = context.config

# La URL de conexión viene de settings (.env), nunca hardcodeada en alembic.ini
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata objetivo para el autogenerate — todos los modelos SQLModel registrados
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Corre las migraciones en modo 'offline': genera SQL sin conectarse a la BD."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configura el contexto de Alembic sobre una conexión síncrona y corre las migraciones."""
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Corre las migraciones en modo 'online', conectándose a la BD de forma async (asyncpg)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
