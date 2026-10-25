"""Pruebas del aislamiento multiempresa en la base de datos (DEC-010, DEC-014, DEC-021).

Cubren la sección "Validación" de DEC-010: la consulta sin filtro solo ve el tenant fijado,
sin tenant no se ve nada, WITH CHECK rechaza inserciones ajenas, el tenant sobrevive al
commit y no se filtra entre conexiones reutilizadas, el rol de la app no omite la RLS y
solo la lista cerrada usa la sesión del sistema.
"""
import ast
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import CLAVE_TENANT, con_tenant
from app.core.security import hash_password
from app.models.area import Area
from app.models.base import utcnow
from app.models.candidato import Candidato
from app.models.usuario import Empresa, RolUsuario, TipoToken, TokenAcceso, Usuario
from app.models.vacante import EstadoVacante, Vacante
from tests.conftest import TENANT_ID, TENANT_ID_OTRO, UrlsPrueba

DIRECTORIO_APP = Path(__file__).resolve().parent.parent / "app"

# Lista cerrada de operaciones con la sesión del sistema (DEC-010 punto 5, DEC-014, DEC-021).
LISTA_CERRADA = {
    ("routers/auth.py", "login"),
    ("routers/publico.py", "obtener_vacante_publica"),
    ("routers/publico.py", "enviar_postulacion"),
    ("routers/publico.py", "listar_vacantes_publicas"),
    ("routers/vacantes.py", "feed_xml_vacante"),
    ("routers/evaluaciones.py", "resolver_codigo_candidato"),
}


def _sesion(engine: AsyncEngine, tenant_id: str | None = None) -> AsyncSession:
    info = {CLAVE_TENANT: tenant_id} if tenant_id else {}
    return AsyncSession(engine, expire_on_commit=False, info=info)


async def _crear_proceso(engine: AsyncEngine, tenant_id: str, sufijo: str) -> Candidato:
    """Crea área, vacante abierta y candidato del tenant dado; retorna el candidato."""
    async with _sesion(engine, tenant_id) as db:
        area = Area(tenant_id=tenant_id, nombre=f"Área {sufijo}", codigo_corto=f"A{sufijo}")
        db.add(area)
        await db.flush()
        vacante = Vacante(
            tenant_id=tenant_id,
            area_id=area.id,
            codigo=f"A{sufijo}-2026-001",
            titulo=f"Vacante {sufijo}",
            estado=EstadoVacante.ABIERTA,
        )
        db.add(vacante)
        await db.flush()
        candidato = Candidato(
            tenant_id=tenant_id,
            vacante_id=vacante.id,
            nombre="Ana",
            apellidos=sufijo,
            email=f"ana.{sufijo.lower()}@test.vael",
        )
        db.add(candidato)
        await db.commit()
        return candidato


# --- Capa de base de datos -----------------------------------------------------------


async def test_consulta_sin_filtro_solo_devuelve_el_tenant_fijado(db_engine: AsyncEngine) -> None:
    """Prueba central del OE4: con el tenant A fijado, select(Candidato) sin filtro solo ve A."""
    propio = await _crear_proceso(db_engine, TENANT_ID, "A")
    await _crear_proceso(db_engine, TENANT_ID_OTRO, "B")

    async with _sesion(db_engine, TENANT_ID) as db:
        candidatos = (await db.exec(select(Candidato))).all()

    assert [c.id for c in candidatos] == [propio.id]


async def test_sin_tenant_fijado_no_se_ve_ninguna_fila(db_engine: AsyncEngine) -> None:
    """Sin app.tenant_id, vael_app no ve filas aunque existan (falla de forma segura)."""
    await _crear_proceso(db_engine, TENANT_ID, "A")

    async with _sesion(db_engine) as db:
        total = (await db.exec(select(func.count()).select_from(Candidato))).one()

    assert total == 0


async def test_insert_con_tenant_ajeno_es_rechazado(db_engine: AsyncEngine) -> None:
    """WITH CHECK impide escribir filas de otra empresa aunque la app lo intente."""
    async with _sesion(db_engine, TENANT_ID) as db:
        db.add(Area(tenant_id=TENANT_ID_OTRO, nombre="Intrusa", codigo_corto="X"))
        with pytest.raises(DBAPIError, match="row-level security"):
            await db.commit()


async def test_el_tenant_del_contexto_sobrevive_al_commit(db_engine: AsyncEngine) -> None:
    """Tras un commit, la transacción siguiente de la misma petición conserva el tenant."""
    with con_tenant(TENANT_ID):
        async with _sesion(db_engine) as db:
            db.add(Area(tenant_id=TENANT_ID, nombre="Primera", codigo_corto="P1"))
            await db.commit()
            db.add(Area(tenant_id=TENANT_ID, nombre="Segunda", codigo_corto="P2"))
            await db.commit()
            nombres = sorted(a.nombre for a in (await db.exec(select(Area))).all())

    assert nombres == ["Primera", "Segunda"]


async def test_conexion_reutilizada_no_mezcla_tenants(urls_prueba: UrlsPrueba, db_engine: AsyncEngine) -> None:
    """Dos peticiones seguidas de empresas distintas sobre la misma conexión del pool no se mezclan."""
    await _crear_proceso(db_engine, TENANT_ID, "A")
    await _crear_proceso(db_engine, TENANT_ID_OTRO, "B")

    # Pool de una sola conexión: las tres sesiones usan la misma conexión física.
    engine = create_async_engine(urls_prueba.app, pool_size=1, max_overflow=0)
    try:
        vistos: list[tuple[int, list[str], str | None]] = []
        for tenant in (TENANT_ID, TENANT_ID_OTRO, None):
            async with _sesion(engine, tenant) as db:
                pid = (await db.exec(text("SELECT pg_backend_pid()"))).one()[0]
                tenants = sorted({a.tenant_id for a in (await db.exec(select(Area))).all()})
            async with engine.connect() as conexion:
                # Fuera de la transacción de la sesión, el valor ya no existe en la conexión.
                residual = (await conexion.execute(text("SELECT current_setting('app.tenant_id', true)"))).scalar()
            vistos.append((pid, tenants, residual or None))
    finally:
        await engine.dispose()

    assert len({pid for pid, _, _ in vistos}) == 1
    assert [tenants for _, tenants, _ in vistos] == [[TENANT_ID], [TENANT_ID_OTRO], []]
    assert all(residual is None for _, _, residual in vistos)


async def test_el_rol_de_la_app_no_omite_la_rls(db_engine: AsyncEngine, system_engine: AsyncEngine) -> None:
    """vael_app no es superusuario ni tiene BYPASSRLS; vael_system sí tiene BYPASSRLS."""
    consulta = text("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    async with db_engine.connect() as conexion:
        app_rol = (await conexion.execute(consulta)).one()
    async with system_engine.connect() as conexion:
        system_rol = (await conexion.execute(consulta)).one()

    assert tuple(app_rol) == ("vael_app", False, False)
    assert tuple(system_rol) == ("vael_system", False, True)


async def test_toda_tabla_con_tenant_tiene_rls_forzada_y_politica(db_engine: AsyncEngine) -> None:
    """Ninguna tabla con tenant_id queda sin RLS: protege también las tablas futuras."""
    tablas = sorted(t.name for t in SQLModel.metadata.sorted_tables if "tenant_id" in t.columns)
    consulta = text(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
        "EXISTS (SELECT 1 FROM pg_policies p WHERE p.tablename = c.relname "
        "        AND p.policyname = 'aislamiento_tenant') "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = ANY(:tablas)"
    )
    async with db_engine.connect() as conexion:
        filas = (await conexion.execute(consulta, {"tablas": tablas})).all()

    estado = {nombre: (rls, forzada, politica) for nombre, rls, forzada, politica in filas}
    assert sorted(estado) == tablas
    sin_rls = [nombre for nombre, valores in estado.items() if valores != (True, True, True)]
    assert sin_rls == []


def test_solo_la_lista_cerrada_usa_la_sesion_del_sistema() -> None:
    """Solo las operaciones de la lista cerrada dependen de get_system_db (DEC-010, DEC-014, DEC-021)."""
    usos: set[tuple[str, str]] = set()
    fuera_de_funciones: list[str] = []
    for archivo in DIRECTORIO_APP.rglob("*.py"):
        relativo = archivo.relative_to(DIRECTORIO_APP).as_posix()
        if relativo == "core/database.py":
            continue
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Name) and nodo.id in {"_system_session_factory", "system_engine"}:
                fuera_de_funciones.append(relativo)
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nombres = {n.id for n in ast.walk(nodo) if isinstance(n, ast.Name)}
                if "get_system_db" in nombres:
                    usos.add((relativo, nodo.name))

    assert fuera_de_funciones == []
    assert usos == LISTA_CERRADA


# --- Capa HTTP: el tenant del JWT llega a la base -----------------------------------


async def test_api_no_muestra_areas_de_otra_empresa(
    client: TestClient, admin_headers: dict[str, str], db_engine: AsyncEngine
) -> None:
    """El admin del tenant A no ve ni obtiene por id un área del tenant B."""
    async with _sesion(db_engine, TENANT_ID_OTRO) as db:
        ajena = Area(tenant_id=TENANT_ID_OTRO, nombre="Ajena", codigo_corto="AJ")
        db.add(ajena)
        await db.commit()

    listar = client.get("/api/areas", headers=admin_headers)
    assert listar.status_code == 200
    assert all(a["id"] != ajena.id for a in listar.json())
    assert client.get(f"/api/areas/{ajena.id}", headers=admin_headers).status_code == 404


async def test_login_y_refresh_funcionan_con_rls(client: TestClient, db_session: AsyncSession) -> None:
    """El login busca por email con la sesión del sistema; el refresh fija el tenant del token."""
    db_session.add(
        Usuario(
            tenant_id=TENANT_ID,
            nombre="Lucía",
            apellidos="Admin",
            email="lucia@test.vael",
            password_hash=await hash_password("clave-segura-123"),
            rol=RolUsuario.ADMIN,
        )
    )
    await db_session.commit()

    login = client.post("/api/auth/login", json={"email": "lucia@test.vael", "password": "clave-segura-123"})
    assert login.status_code == 200, login.text

    refresco = client.post("/api/auth/refresh", json={"refresh_token": login.json()["refresh_token"]})
    assert refresco.status_code == 200, refresco.text

    perfil = client.get("/api/auth/perfil", headers={"Authorization": f"Bearer {refresco.json()['access_token']}"})
    assert perfil.status_code == 200
    assert perfil.json()["email"] == "lucia@test.vael"


async def test_email_de_otra_empresa_responde_409(
    client: TestClient, admin_headers: dict[str, str], db_engine: AsyncEngine
) -> None:
    """El email es único en la plataforma aunque la RLS oculte al usuario de la otra empresa."""
    async with _sesion(db_engine, TENANT_ID_OTRO) as db:
        db.add(
            Usuario(
                tenant_id=TENANT_ID_OTRO,
                nombre="Otro",
                apellidos="Usuario",
                email="repetido@test.vael",
                password_hash="x",
                rol=RolUsuario.RECLUTADOR,
            )
        )
        await db.commit()

    respuesta = client.post(
        "/api/auth/usuarios/crear",
        json={"nombre": "Nuevo", "apellidos": "Usuario", "email": "repetido@test.vael", "rol": "reclutador"},
        headers=admin_headers,
    )
    assert respuesta.status_code == 409


async def test_rutas_publicas_cruzan_empresas_con_la_sesion_del_sistema(
    client: TestClient, db_engine: AsyncEngine
) -> None:
    """Listado público, vacante por código y feed XML funcionan sin JWT (DEC-010, DEC-014)."""
    for tenant, sufijo in ((TENANT_ID, "A"), (TENANT_ID_OTRO, "B")):
        async with _sesion(db_engine, tenant) as db:
            db.add(Empresa(tenant_id=tenant, nombre=f"Empresa {sufijo}"))
            await db.commit()
        await _crear_proceso(db_engine, tenant, sufijo)

    listado = client.get("/api/publico/vacantes")
    assert listado.status_code == 200
    assert {v["codigo"] for v in listado.json()} >= {"AA-2026-001", "AB-2026-001"}

    assert client.get("/api/publico/postular/AB-2026-001").status_code == 200

    async with _sesion(db_engine, TENANT_ID_OTRO) as db:
        vacante = (await db.exec(select(Vacante))).one()
    feed = client.get(f"/api/vacantes/{vacante.id}/feed-xml")
    assert feed.status_code == 200
    assert feed.headers["content-type"].startswith("application/xml")

    # DEC-014: una vacante que no está abierta no se expone en el feed.
    async with _sesion(db_engine, TENANT_ID_OTRO) as db:
        borrador = Vacante(
            tenant_id=TENANT_ID_OTRO,
            area_id=vacante.area_id,
            codigo="AB-2026-002",
            titulo="Borrador",
            estado=EstadoVacante.BORRADOR,
        )
        db.add(borrador)
        await db.commit()
    assert client.get(f"/api/vacantes/{borrador.id}/feed-xml").status_code == 404


async def test_resolver_codigo_del_candidato_con_rls(client: TestClient, db_engine: AsyncEngine) -> None:
    """El código corto se resuelve sin conocer la empresa, con la sesión del sistema (DEC-021)."""
    candidato = await _crear_proceso(db_engine, TENANT_ID_OTRO, "B")
    async with _sesion(db_engine, TENANT_ID_OTRO) as db:
        db.add(
            TokenAcceso(
                tenant_id=TENANT_ID_OTRO,
                candidato_id=candidato.id,
                token="jwt-de-prueba",
                codigo_corto="VAEL-ABCD-EFGH",
                tipo=TipoToken.EXAMEN,
                expira_en=utcnow() + timedelta(days=1),
            )
        )
        await db.commit()

    respuesta = client.post("/api/evaluaciones/candidato/resolver-codigo", json={"codigo_corto": "VAEL-ABCD-EFGH"})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"token": "jwt-de-prueba"}
