"""Motores de base de datos, sesiones async y fijación del tenant para la RLS (DEC-010).

Dos sesiones:
- La normal (`get_db`, `async_session_factory`) se conecta como `vael_app`, sin
  superusuario ni BYPASSRLS: PostgreSQL solo deja ver y modificar las filas del tenant
  fijado en `app.tenant_id`. Sin tenant fijado no ve ninguna fila (falla de forma segura).
- La del sistema (`get_system_db`) se conecta como `vael_system`, con BYPASSRLS, y solo
  la usa la lista cerrada de DEC-010, DEC-014 y DEC-021. El test
  tests/test_rls.py::test_solo_la_lista_cerrada_usa_la_sesion_del_sistema lo verifica.

El tenant se fija al inicio de cada transacción con el evento `after_begin`, así no se
pierde tras un commit ni se filtra entre peticiones que reutilizan conexiones del pool.
"""
from collections.abc import AsyncGenerator, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, SessionTransaction
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

# Tenant de la petición o tarea en curso. Lo fija dependencies.py a partir del JWT.
_tenant_actual: ContextVar[str | None] = ContextVar("tenant_bd", default=None)

# Clave de Session.info para fijar el tenant de una sesión concreta (tests y procesos sin petición).
CLAVE_TENANT = "tenant_id"


def fijar_tenant(tenant_id: str) -> None:
    """Fija el tenant del contexto actual; las transacciones siguientes lo aplican a la RLS."""
    _tenant_actual.set(tenant_id)


@contextmanager
def con_tenant(tenant_id: str) -> Iterator[None]:
    """Fija el tenant dentro de un bloque y restaura el anterior al salir."""
    token = _tenant_actual.set(tenant_id)
    try:
        yield
    finally:
        _tenant_actual.reset(token)


def tenant_fijado() -> str | None:
    """Retorna el tenant fijado en el contexto actual, o None si no hay ninguno."""
    return _tenant_actual.get()


@event.listens_for(Session, "after_begin")
def _aplicar_tenant_en_transaccion(session: Session, _transaccion: SessionTransaction, conexion: Connection) -> None:
    """Ejecuta set_config('app.tenant_id', ..., true) al inicio de cada transacción.

    El tercer argumento `true` limita el valor a la transacción: al terminar se descarta,
    así una conexión devuelta al pool no conserva el tenant de la petición anterior.
    """
    tenant_id = session.info.get(CLAVE_TENANT) or _tenant_actual.get()
    if tenant_id:
        conexion.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})


def _crear_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, echo=settings.debug, future=True)


engine: AsyncEngine = _crear_engine(settings.database_url)
system_engine: AsyncEngine = _crear_engine(settings.database_system_url)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

_system_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=system_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def sesion_con_tenant(tenant_id: str, **kwargs: Any) -> AsyncSession:
    """Abre una sesión normal (`vael_app`) con el tenant fijado, para procesos fuera de una petición."""
    return async_session_factory(info={CLAVE_TENANT: tenant_id}, **kwargs)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI: sesión normal (`vael_app`), sujeta a la RLS del tenant del JWT."""
    async with async_session_factory() as session:
        yield session


async def get_system_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI: sesión del sistema (`vael_system`, BYPASSRLS).

    Solo para la lista cerrada (DEC-010, DEC-014, DEC-021): login, postulación pública por
    código, listado público de vacantes, feed XML y resolución del código del candidato.
    Usarla en otra operación requiere un ADR.
    """
    async with _system_session_factory() as session:
        yield session
