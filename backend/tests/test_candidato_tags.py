"""Pruebas de candidato_tags y del filtro por etiqueta de GET /api/candidatos (DEV-C-05).

La RLS de la tabla la cubre además tests/test_rls.py, que exige política en toda tabla con
tenant_id.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import CLAVE_TENANT
from app.models.area import Area
from app.models.candidato import Candidato, CandidatoTag, Tag
from app.models.vacante import EstadoVacante, Vacante
from tests.conftest import TENANT_ID, TENANT_ID_OTRO


def _sesion(engine: AsyncEngine, tenant_id: str) -> AsyncSession:
    return AsyncSession(engine, expire_on_commit=False, info={CLAVE_TENANT: tenant_id})


async def _crear_candidatos(engine: AsyncEngine, tenant_id: str, sufijo: str, cantidad: int) -> list[Candidato]:
    """Crea un área, una vacante abierta y `cantidad` candidatos del tenant dado."""
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
        candidatos = [
            Candidato(
                tenant_id=tenant_id,
                vacante_id=vacante.id,
                nombre=f"Candidato {i}",
                apellidos=sufijo,
                email=f"c{i}.{sufijo.lower()}@test.vael",
            )
            for i in range(cantidad)
        ]
        db.add_all(candidatos)
        await db.commit()
        return candidatos


async def _etiquetar(engine: AsyncEngine, tenant_id: str, nombre: str, candidatos: list[Candidato]) -> Tag:
    """Crea una etiqueta del tenant y se la asigna a los candidatos dados."""
    async with _sesion(engine, tenant_id) as db:
        tag = Tag(tenant_id=tenant_id, nombre=nombre, color="#0E5C4A")
        db.add(tag)
        await db.flush()
        db.add_all(CandidatoTag(tenant_id=tenant_id, candidato_id=c.id, tag_id=tag.id) for c in candidatos)
        await db.commit()
        return tag


async def test_listado_filtra_por_etiqueta(
    client: TestClient, admin_headers: dict[str, str], db_engine: AsyncEngine
) -> None:
    """Con tag_id solo aparecen los candidatos que tienen esa etiqueta; sin él, todos."""
    candidatos = await _crear_candidatos(db_engine, TENANT_ID, "TAG", 3)
    tag = await _etiquetar(db_engine, TENANT_ID, "Senior", candidatos[:2])
    await _etiquetar(db_engine, TENANT_ID, "Remoto", candidatos[1:])

    filtrado = client.get("/api/candidatos", params={"tag_id": tag.id}, headers=admin_headers)
    assert filtrado.status_code == 200, filtrado.text
    assert sorted(c["id"] for c in filtrado.json()) == sorted(c.id for c in candidatos[:2])

    todos = client.get("/api/candidatos", headers=admin_headers)
    assert len(todos.json()) == 3


async def test_filtro_combinado_con_estado_y_etiqueta_inexistente(
    client: TestClient, admin_headers: dict[str, str], db_engine: AsyncEngine
) -> None:
    """El filtro por etiqueta se combina con los demás; una etiqueta inexistente no devuelve nada."""
    candidatos = await _crear_candidatos(db_engine, TENANT_ID, "CMB", 2)
    tag = await _etiquetar(db_engine, TENANT_ID, "Senior", candidatos)

    con_estado = client.get(
        "/api/candidatos", params={"tag_id": tag.id, "estado": "finalista"}, headers=admin_headers
    )
    assert con_estado.json() == []

    inexistente = client.get("/api/candidatos", params={"tag_id": "no-existe"}, headers=admin_headers)
    assert inexistente.status_code == 200
    assert inexistente.json() == []


async def test_etiqueta_de_otra_empresa_no_filtra_candidatos_ajenos(
    client: TestClient, admin_headers: dict[str, str], db_engine: AsyncEngine
) -> None:
    """Filtrar por el id de una etiqueta de otra empresa no expone a sus candidatos."""
    ajenos = await _crear_candidatos(db_engine, TENANT_ID_OTRO, "OTR", 2)
    tag_ajeno = await _etiquetar(db_engine, TENANT_ID_OTRO, "Senior", ajenos)

    respuesta = client.get("/api/candidatos", params={"tag_id": tag_ajeno.id}, headers=admin_headers)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


async def test_rls_oculta_las_asignaciones_de_otra_empresa(db_engine: AsyncEngine) -> None:
    """Sin filtro de aplicación, la RLS solo deja ver las asignaciones del tenant fijado."""
    propios = await _crear_candidatos(db_engine, TENANT_ID, "PRO", 1)
    ajenos = await _crear_candidatos(db_engine, TENANT_ID_OTRO, "AJE", 1)
    await _etiquetar(db_engine, TENANT_ID, "Senior", propios)
    await _etiquetar(db_engine, TENANT_ID_OTRO, "Senior", ajenos)

    async with _sesion(db_engine, TENANT_ID) as db:
        filas = (await db.exec(select(CandidatoTag))).all()
    assert [f.candidato_id for f in filas] == [propios[0].id]


async def test_la_misma_etiqueta_no_se_asigna_dos_veces(db_engine: AsyncEngine) -> None:
    """La clave primaria (candidato_id, tag_id) impide duplicar una asignación."""
    candidatos = await _crear_candidatos(db_engine, TENANT_ID, "DUP", 1)
    tag = await _etiquetar(db_engine, TENANT_ID, "Senior", candidatos)

    async with _sesion(db_engine, TENANT_ID) as db:
        db.add(CandidatoTag(tenant_id=TENANT_ID, candidato_id=candidatos[0].id, tag_id=tag.id))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_borrar_la_etiqueta_borra_sus_asignaciones(db_engine: AsyncEngine) -> None:
    """DELETE /tags/{id} elimina la etiqueta y sus asignaciones (doc 06): la FK es en cascada."""
    candidatos = await _crear_candidatos(db_engine, TENANT_ID, "DEL", 2)
    tag = await _etiquetar(db_engine, TENANT_ID, "Senior", candidatos)

    async with _sesion(db_engine, TENANT_ID) as db:
        await db.delete(await db.get(Tag, tag.id))
        await db.commit()

    async with _sesion(db_engine, TENANT_ID) as db:
        restantes = (await db.exec(select(CandidatoTag).where(CandidatoTag.tag_id == tag.id))).all()
        candidatos_vivos = (await db.exec(select(Candidato))).all()
    assert restantes == []
    assert len(candidatos_vivos) == 2
