"""Pruebas del banco de talento (RF-A-17, HU-14) — DEV-A-08.

`Candidato.en_banco_talento` solo lo marca RRHH explícitamente desde el detalle del candidato
(`POST /candidatos/{id}/banco-talento`); `GET /candidatos/banco-talento` solo lista a quienes
tienen esa marca, con filtro opcional por área. El permiso de escritura (reclutador o superior)
ya lo cubre `test_permisos_por_rol.py`, que recorre todas las rutas de escritura y exige 403 al
evaluador sin que haga falta repetirlo aquí.
"""
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import CLAVE_TENANT
from app.core.security import create_access_token
from app.models.area import Area
from app.models.candidato import EstadoCandidato
from app.models.usuario import RolUsuario, Usuario
from app.models.vacante import EstadoVacante, Vacante
from tests.conftest import TENANT_ID, TENANT_ID_OTRO
from tests.test_decisiones import _candidato, _vacante
from tests.test_metricas import _candidato_de, _vacante_de


async def test_enviar_al_banco_marca_el_campo_y_es_idempotente(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.CV_RECHAZADO, sufijo="a")
    assert candidato.en_banco_talento is False

    primera = client.post(f"/api/candidatos/{candidato.id}/banco-talento", headers=admin_headers)
    assert primera.status_code == 200, primera.text
    assert primera.json()["en_banco_talento"] is True

    segunda = client.post(f"/api/candidatos/{candidato.id}/banco-talento", headers=admin_headers)
    assert segunda.status_code == 200, segunda.text
    assert segunda.json()["en_banco_talento"] is True


async def test_enviar_al_banco_de_un_candidato_inexistente_responde_404(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    respuesta = client.post("/api/candidatos/no-existe/banco-talento", headers=admin_headers)
    assert respuesta.status_code == 404


async def test_banco_talento_solo_lista_a_los_marcados(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    vacante = await _vacante(db_session)
    marcado = await _candidato(db_session, vacante, EstadoCandidato.DESCARTADO, sufijo="marcado")
    sin_marcar = await _candidato(db_session, vacante, EstadoCandidato.CV_RECHAZADO, sufijo="libre")

    assert client.post(f"/api/candidatos/{marcado.id}/banco-talento", headers=admin_headers).status_code == 200

    respuesta = client.get("/api/candidatos/banco-talento", headers=admin_headers)
    assert respuesta.status_code == 200, respuesta.text
    ids = {c["id"] for c in respuesta.json()}
    assert ids == {marcado.id}
    assert sin_marcar.id not in ids


async def test_banco_talento_filtra_por_area(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    area_ti = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI")
    area_ven = Area(tenant_id=TENANT_ID, nombre="Comercial", codigo_corto="VEN")
    db_session.add_all([area_ti, area_ven])
    await db_session.flush()
    vacante_ti = Vacante(tenant_id=TENANT_ID, area_id=area_ti.id, codigo="TI-2026-900", titulo="Dev", estado=EstadoVacante.ABIERTA)
    vacante_ven = Vacante(tenant_id=TENANT_ID, area_id=area_ven.id, codigo="VEN-2026-900", titulo="Ejecutivo", estado=EstadoVacante.ABIERTA)
    db_session.add_all([vacante_ti, vacante_ven])
    await db_session.commit()

    de_ti = await _candidato(db_session, vacante_ti, EstadoCandidato.DESCARTADO, sufijo="ti")
    de_ven = await _candidato(db_session, vacante_ven, EstadoCandidato.DESCARTADO, sufijo="ven")
    for c in (de_ti, de_ven):
        assert client.post(f"/api/candidatos/{c.id}/banco-talento", headers=admin_headers).status_code == 200

    sin_filtro = client.get("/api/candidatos/banco-talento", headers=admin_headers)
    assert {c["id"] for c in sin_filtro.json()} == {de_ti.id, de_ven.id}

    solo_ti = client.get("/api/candidatos/banco-talento", params={"area_id": area_ti.id}, headers=admin_headers)
    assert solo_ti.status_code == 200, solo_ti.text
    assert {c["id"] for c in solo_ti.json()} == {de_ti.id}


async def test_banco_talento_aisla_entre_empresas(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession, db_engine: AsyncEngine
) -> None:
    """Una empresa no ve en su banco de talento a los candidatos marcados por otra (DEC-010)."""
    vacante = await _vacante(db_session)
    propio = await _candidato(db_session, vacante, EstadoCandidato.DESCARTADO, sufijo="propio")
    assert client.post(f"/api/candidatos/{propio.id}/banco-talento", headers=admin_headers).status_code == 200

    async with AsyncSession(db_engine, info={CLAVE_TENANT: TENANT_ID_OTRO}, expire_on_commit=False) as otra:
        vacante_ajena = await _vacante_de(otra, TENANT_ID_OTRO, "ajena")
        ajeno = await _candidato_de(otra, TENANT_ID_OTRO, vacante_ajena, EstadoCandidato.DESCARTADO, "ajeno")
        ajeno.en_banco_talento = True
        otra.add(ajeno)
        await otra.commit()

    respuesta = client.get("/api/candidatos/banco-talento", headers=admin_headers)
    assert respuesta.status_code == 200, respuesta.text
    ids = {c["id"] for c in respuesta.json()}
    assert ids == {propio.id}
    assert ajeno.id not in ids


async def test_el_evaluador_no_envia_al_banco_pero_si_lo_consulta(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Listar es Autenticado (cualquier rol); enviar al banco es Reclutador+ (doc 06)."""
    vacante = await _vacante(db_session)
    candidato = await _candidato(db_session, vacante, EstadoCandidato.DESCARTADO, sufijo="a")
    evaluador = Usuario(
        tenant_id=TENANT_ID, nombre="Eva", apellidos="Luadora", email="evaluador@banco.test.vael",
        password_hash="x", rol=RolUsuario.EVALUADOR,
    )
    db_session.add(evaluador)
    await db_session.commit()
    token = await create_access_token(evaluador.id, TENANT_ID, evaluador.rol.value)
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post(f"/api/candidatos/{candidato.id}/banco-talento", headers=headers).status_code == 403
    assert client.get("/api/candidatos/banco-talento", headers=headers).status_code == 200
