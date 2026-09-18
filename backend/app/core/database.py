"""Motor de base de datos y gestión de sesiones async con SQLModel."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

engine: AsyncEngine = create_async_engine(settings.database_url, echo=settings.debug, future=True)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Crea las tablas en la base de datos a partir de los modelos SQLModel registrados."""
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que entrega una sesión async de base de datos por request."""
    async with async_session_factory() as session:
        yield session
