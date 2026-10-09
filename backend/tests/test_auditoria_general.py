"""Pruebas de GET /api/evaluaciones/auditoria — auditoría general del tenant."""
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.area import Area
from app.models.candidato import Candidato
from app.models.evaluacion import Examen, EventoAuditoria, SeveridadEvento
from app.models.vacante import Vacante
from tests.conftest import TENANT_ID


def test_sin_token_responde_403(client: TestClient) -> None:
    """GET sin header Authorization -> 403."""
    response = client.get("/api/evaluaciones/auditoria")
    assert response.status_code == 403


def test_lista_vacia_para_tenant_sin_eventos(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Tenant nuevo, sin examenes/entrevistas/eventos -> lista vacía."""
    response = client.get("/api/evaluaciones/auditoria", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


async def _crear_evento_de_examen(db_session: AsyncSession) -> tuple[str, str, str]:
    """Crea área/vacante/candidato/examen/evento mínimos y retorna (candidato_id, examen_id, evento_id)."""
    area = Area(tenant_id=TENANT_ID, nombre="Tecnología", codigo_corto="TI")
    db_session.add(area)
    await db_session.commit()
    await db_session.refresh(area)

    vacante = Vacante(tenant_id=TENANT_ID, area_id=area.id, codigo="TI-2026-001", titulo="Dev")
    db_session.add(vacante)
    await db_session.commit()
    await db_session.refresh(vacante)

    candidato = Candidato(
        tenant_id=TENANT_ID, vacante_id=vacante.id, nombre="Ana", apellidos="Lopez", email="ana@test.vael"
    )
    db_session.add(candidato)
    await db_session.commit()
    await db_session.refresh(candidato)

    examen = Examen(tenant_id=TENANT_ID, candidato_id=candidato.id, vacante_id=vacante.id)
    db_session.add(examen)
    await db_session.commit()
    await db_session.refresh(examen)

    evento = EventoAuditoria(
        tenant_id=TENANT_ID,
        examen_id=examen.id,
        tipo="copy_paste",
        severidad=SeveridadEvento.ALTA,
        detalle="Pegado detectado en pregunta 3",
    )
    db_session.add(evento)
    await db_session.commit()
    await db_session.refresh(evento)

    return candidato.id, examen.id, evento.id


async def test_incluye_eventos_de_examen_con_candidato_resuelto(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """Un evento de examen aparece en la auditoría general con su candidato_id resuelto."""
    candidato_id, examen_id, evento_id = await _crear_evento_de_examen(db_session)

    response = client.get("/api/evaluaciones/auditoria", headers=admin_headers)
    assert response.status_code == 200
    eventos = response.json()
    assert len(eventos) == 1
    assert eventos[0]["id"] == evento_id
    assert eventos[0]["examen_id"] == examen_id
    assert eventos[0]["entrevista_id"] is None
    assert eventos[0]["candidato_id"] == candidato_id
    assert eventos[0]["severidad"] == "alta"


async def test_filtro_por_severidad(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """?severidad=baja no matchea un evento de severidad alta -> lista vacía."""
    await _crear_evento_de_examen(db_session)

    response = client.get("/api/evaluaciones/auditoria?severidad=baja", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_filtro_por_candidato_id_sin_eventos_propios(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """Filtrar por un candidato_id que no tiene examenes/entrevistas -> lista vacía (no explota)."""
    await _crear_evento_de_examen(db_session)

    response = client.get(
        "/api/evaluaciones/auditoria?candidato_id=otro-candidato-sin-relacion", headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json() == []
