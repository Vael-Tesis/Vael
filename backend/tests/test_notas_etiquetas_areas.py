"""Pruebas de DEV-A-01: etiquetas (HU-13), edición y borrado de notas (HU-13) y gestión de áreas (HU-05)."""
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import CLAVE_TENANT
from app.core.security import create_access_token
from app.models.area import Area
from app.models.candidato import Candidato, Tag
from app.models.usuario import RolUsuario, Usuario
from app.models.vacante import EstadoVacante, Vacante
from tests.conftest import TENANT_ID, TENANT_ID_OTRO


async def _candidato(db: AsyncSession, codigo_area: str = "TI") -> Candidato:
    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto=codigo_area)
    db.add(area)
    await db.flush()
    vacante = Vacante(
        tenant_id=TENANT_ID, area_id=area.id, codigo=f"{codigo_area}-2026-001", titulo="Backend", estado=EstadoVacante.ABIERTA
    )
    db.add(vacante)
    await db.flush()
    candidato = Candidato(tenant_id=TENANT_ID, vacante_id=vacante.id, nombre="Ana", apellidos="Ruiz", email="ana@example.com")
    db.add(candidato)
    await db.commit()
    return candidato


async def _headers_de(db: AsyncSession, rol: RolUsuario, email: str) -> dict[str, str]:
    usuario = Usuario(tenant_id=TENANT_ID, nombre="Otro", apellidos=rol.value, email=email, password_hash="x", rol=rol)
    db.add(usuario)
    await db.commit()
    return {"Authorization": f"Bearer {await create_access_token(usuario.id, TENANT_ID, rol.value)}"}


# --- Etiquetas ----------------------------------------------------------------------------


def test_crud_de_etiquetas(client: TestClient, admin_headers: dict[str, str]) -> None:
    creada = client.post("/api/tags", json={"nombre": "Senior", "color": "#0E5C4A"}, headers=admin_headers)
    assert creada.status_code == 201, creada.text
    tag = creada.json()

    duplicada = client.post("/api/tags", json={"nombre": " senior "}, headers=admin_headers)
    assert duplicada.status_code == 409

    color_invalido = client.post("/api/tags", json={"nombre": "Remoto", "color": "verde"}, headers=admin_headers)
    assert color_invalido.status_code == 422

    editada = client.put(f"/api/tags/{tag['id']}", json={"nombre": "Senior+", "color": "#C9A227"}, headers=admin_headers)
    assert editada.status_code == 200
    assert editada.json() == {"id": tag["id"], "nombre": "Senior+", "color": "#C9A227"}

    assert [t["nombre"] for t in client.get("/api/tags", headers=admin_headers).json()] == ["Senior+"]
    assert client.delete(f"/api/tags/{tag['id']}", headers=admin_headers).status_code == 200
    assert client.get("/api/tags", headers=admin_headers).json() == []


async def test_asignar_es_idempotente_y_quitar_responde_404_si_no_estaba(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    candidato = await _candidato(db_session)
    tag = client.post("/api/tags", json={"nombre": "Senior"}, headers=admin_headers).json()
    ruta = f"/api/candidatos/{candidato.id}/tags"

    primera = client.post(ruta, json={"tag_id": tag["id"]}, headers=admin_headers)
    segunda = client.post(ruta, json={"tag_id": tag["id"]}, headers=admin_headers)
    assert primera.status_code == 200 and segunda.status_code == 200
    assert [t["id"] for t in segunda.json()] == [tag["id"]]

    detalle = client.get(f"/api/candidatos/{candidato.id}", headers=admin_headers).json()
    assert [t["nombre"] for t in detalle["tags"]] == ["Senior"]
    filtrado = client.get("/api/candidatos", params={"tag_id": tag["id"]}, headers=admin_headers).json()
    assert [c["id"] for c in filtrado] == [candidato.id]

    assert client.delete(f"{ruta}/{tag['id']}", headers=admin_headers).json() == []
    assert client.delete(f"{ruta}/{tag['id']}", headers=admin_headers).status_code == 404


async def test_eliminar_la_etiqueta_borra_sus_asignaciones(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    candidato = await _candidato(db_session)
    tag = client.post("/api/tags", json={"nombre": "Senior"}, headers=admin_headers).json()
    client.post(f"/api/candidatos/{candidato.id}/tags", json={"tag_id": tag["id"]}, headers=admin_headers)

    assert client.delete(f"/api/tags/{tag['id']}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/candidatos/{candidato.id}", headers=admin_headers).json()["tags"] == []


async def test_permisos_de_etiquetas(
    client: TestClient, reclutador_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """El reclutador crea y asigna, pero no elimina; el evaluador solo consulta."""
    tag = client.post("/api/tags", json={"nombre": "Senior"}, headers=reclutador_headers)
    assert tag.status_code == 201
    assert client.delete(f"/api/tags/{tag.json()['id']}", headers=reclutador_headers).status_code == 403

    evaluador = await _headers_de(db_session, RolUsuario.EVALUADOR, "evaluador@test.vael")
    assert client.get("/api/tags", headers=evaluador).status_code == 200
    assert client.post("/api/tags", json={"nombre": "Otra"}, headers=evaluador).status_code == 403


async def test_no_se_asigna_una_etiqueta_de_otra_empresa(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, db_engine: AsyncEngine
) -> None:
    candidato = await _candidato(db_session)
    async with AsyncSession(db_engine, info={CLAVE_TENANT: TENANT_ID_OTRO}, expire_on_commit=False) as otra:
        ajena = Tag(tenant_id=TENANT_ID_OTRO, nombre="Ajena")
        otra.add(ajena)
        await otra.commit()

    respuesta = client.post(f"/api/candidatos/{candidato.id}/tags", json={"tag_id": ajena.id}, headers=admin_headers)
    assert respuesta.status_code == 404
    assert client.put(f"/api/tags/{ajena.id}", json={"nombre": "X"}, headers=admin_headers).status_code == 404


# --- Notas ----------------------------------------------------------------------------------


async def test_solo_el_autor_edita_y_el_autor_o_un_admin_eliminan(
    client: TestClient, admin_headers: dict[str, str], reclutador_headers: dict[str, str], db_session: AsyncSession
) -> None:
    candidato = await _candidato(db_session)
    ruta = f"/api/candidatos/{candidato.id}/notas"
    nota = client.post(ruta, json={"contenido": "Buena comunicación"}, headers=reclutador_headers).json()
    assert nota["updated_at"] is None
    assert nota["autor_nombre"] == "Test reclutador"

    assert client.put(f"{ruta}/{nota['id']}", json={"contenido": "Editada"}, headers=admin_headers).status_code == 403
    editada = client.put(f"{ruta}/{nota['id']}", json={"contenido": "Editada"}, headers=reclutador_headers)
    assert editada.status_code == 200
    assert editada.json()["contenido"] == "Editada" and editada.json()["updated_at"] is not None

    listado = client.get(ruta, headers=admin_headers).json()
    assert [(n["contenido"], n["autor_nombre"]) for n in listado] == [("Editada", "Test reclutador")]

    otra = client.post(ruta, json={"contenido": "Del gerente"}, headers=await _headers_de(db_session, RolUsuario.GERENTE, "g@test.vael")).json()
    assert client.delete(f"{ruta}/{otra['id']}", headers=reclutador_headers).status_code == 403
    assert client.delete(f"{ruta}/{otra['id']}", headers=admin_headers).status_code == 200
    assert client.delete(f"{ruta}/{nota['id']}", headers=reclutador_headers).status_code == 200
    assert client.get(ruta, headers=admin_headers).json() == []
    assert client.delete(f"{ruta}/{nota['id']}", headers=admin_headers).status_code == 404


# --- Áreas ----------------------------------------------------------------------------------


def test_activar_y_desactivar_un_area(client: TestClient, admin_headers: dict[str, str]) -> None:
    area = client.post("/api/areas", json={"nombre": "Comercial", "codigo_corto": "VEN"}, headers=admin_headers).json()

    desactivada = client.post(f"/api/areas/{area['id']}/desactivar", headers=admin_headers)
    assert desactivada.status_code == 200 and desactivada.json()["activa"] is False
    assert client.get("/api/areas", params={"activa": True}, headers=admin_headers).json() == []

    activada = client.post(f"/api/areas/{area['id']}/activar", headers=admin_headers)
    assert activada.json()["activa"] is True


def test_el_codigo_corto_es_unico_en_la_empresa(client: TestClient, admin_headers: dict[str, str]) -> None:
    client.post("/api/areas", json={"nombre": "Comercial", "codigo_corto": "VEN"}, headers=admin_headers)
    otra = client.post("/api/areas", json={"nombre": "Otra", "codigo_corto": "OPE"}, headers=admin_headers).json()

    assert client.post("/api/areas", json={"nombre": "Ventas", "codigo_corto": "ven"}, headers=admin_headers).status_code == 409
    assert client.put(f"/api/areas/{otra['id']}", json={"codigo_corto": "VEN"}, headers=admin_headers).status_code == 409
    assert client.put(f"/api/areas/{otra['id']}", json={"codigo_corto": "OPE"}, headers=admin_headers).status_code == 200


async def test_un_area_con_vacantes_no_se_elimina(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    candidato = await _candidato(db_session, "TI")
    vacante = await db_session.get(Vacante, candidato.vacante_id)
    libre = client.post("/api/areas", json={"nombre": "Libre", "codigo_corto": "LIB"}, headers=admin_headers).json()

    assert client.delete(f"/api/areas/{vacante.area_id}", headers=admin_headers).status_code == 409
    assert client.delete(f"/api/areas/{libre['id']}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/areas/{libre['id']}", headers=admin_headers).status_code == 404


async def test_permisos_de_areas(
    client: TestClient, admin_headers: dict[str, str], reclutador_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """Activar y desactivar: admin o gerente. Eliminar: solo admin."""
    area = client.post("/api/areas", json={"nombre": "Comercial", "codigo_corto": "VEN"}, headers=admin_headers).json()
    gerente = await _headers_de(db_session, RolUsuario.GERENTE, "gerente@test.vael")

    assert client.post(f"/api/areas/{area['id']}/desactivar", headers=reclutador_headers).status_code == 403
    assert client.post(f"/api/areas/{area['id']}/desactivar", headers=gerente).status_code == 200
    assert client.delete(f"/api/areas/{area['id']}", headers=gerente).status_code == 403
