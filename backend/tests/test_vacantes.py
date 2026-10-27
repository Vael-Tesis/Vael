"""Pruebas de vacantes (DEV-A-04): creación y código (HU-08), estados y duplicado (HU-09),
eliminación en borrador y textos de publicación (HU-10)."""
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.candidato import Candidato
from app.routers import vacantes as router_vacantes
from tests.conftest import TENANT_ID

ANIO = datetime.now(timezone.utc).year


def _area(client: TestClient, headers: dict[str, str], codigo: str = "TI") -> dict[str, Any]:
    return client.post("/api/areas", json={"nombre": "Tecnología", "codigo_corto": codigo}, headers=headers).json()


def _vacante(client: TestClient, headers: dict[str, str], area_id: str, titulo: str = "Backend Python") -> dict[str, Any]:
    respuesta = client.post("/api/vacantes", json={"area_id": area_id, "titulo": titulo}, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _accion(client: TestClient, headers: dict[str, str], vacante_id: str, accion: str) -> Any:
    return client.post(f"/api/vacantes/{vacante_id}/{accion}", headers=headers)


def test_se_crea_en_borrador_con_codigo_automatico(client: TestClient, admin_headers: dict[str, str]) -> None:
    area = _area(client, admin_headers)
    primera = _vacante(client, admin_headers, area["id"])
    segunda = _vacante(client, admin_headers, area["id"], "Frontend")

    assert primera["estado"] == "borrador"
    assert primera["codigo"] == f"TI-{ANIO}-001" and segunda["codigo"] == f"TI-{ANIO}-002"
    assert primera["textos_publicacion"] is None


def test_los_cuatro_cambios_de_estado(client: TestClient, admin_headers: dict[str, str]) -> None:
    vacante = _vacante(client, admin_headers, _area(client, admin_headers)["id"])

    assert _accion(client, admin_headers, vacante["id"], "pausar").status_code == 409  # borrador no se pausa
    assert _accion(client, admin_headers, vacante["id"], "publicar").json()["estado"] == "abierta"
    assert _accion(client, admin_headers, vacante["id"], "pausar").json()["estado"] == "pausada"
    assert _accion(client, admin_headers, vacante["id"], "publicar").json()["estado"] == "abierta"  # reactivar
    assert _accion(client, admin_headers, vacante["id"], "cerrar").json()["estado"] == "cerrada"
    reabrir = _accion(client, admin_headers, vacante["id"], "publicar")
    assert reabrir.status_code == 409 and "cerrada" in reabrir.json()["detail"]

    copia = _accion(client, admin_headers, vacante["id"], "duplicar")
    assert copia.status_code == 201
    assert copia.json()["estado"] == "borrador"
    assert copia.json()["codigo"] != vacante["codigo"]


def test_solo_una_vacante_abierta_acepta_postulaciones(client: TestClient, admin_headers: dict[str, str]) -> None:
    vacante = _vacante(client, admin_headers, _area(client, admin_headers)["id"])
    ruta = f"/api/publico/postular/{vacante['codigo']}"

    assert client.get(ruta).status_code == 404  # borrador
    _accion(client, admin_headers, vacante["id"], "publicar")
    assert client.get(ruta).status_code == 200
    _accion(client, admin_headers, vacante["id"], "pausar")
    assert client.get(ruta).status_code == 404


async def test_solo_se_elimina_en_borrador_y_sin_candidatos(
    client: TestClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    area = _area(client, admin_headers)
    borrador = _vacante(client, admin_headers, area["id"])
    con_candidato = _vacante(client, admin_headers, area["id"], "Con candidato")
    abierta = _vacante(client, admin_headers, area["id"], "Abierta")
    _accion(client, admin_headers, abierta["id"], "publicar")
    db_session.add(Candidato(tenant_id=TENANT_ID, vacante_id=con_candidato["id"], nombre="Ana", apellidos="Ruiz", email="ana@example.com"))
    await db_session.commit()

    assert client.delete(f"/api/vacantes/{abierta['id']}", headers=admin_headers).status_code == 409
    assert client.delete(f"/api/vacantes/{con_candidato['id']}", headers=admin_headers).status_code == 409
    assert client.delete(f"/api/vacantes/{borrador['id']}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/vacantes/{borrador['id']}", headers=admin_headers).status_code == 404


def test_los_textos_se_generan_editan_y_guardan(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    vacante = _vacante(client, admin_headers, _area(client, admin_headers)["id"])
    ruta = f"/api/vacantes/{vacante['id']}/textos"

    async def generar_falso(_vacante: Any) -> dict[str, str]:
        return {"linkedin": "Texto para LinkedIn", "whatsapp": "Texto corto", "indeed": "Descripción"}

    monkeypatch.setattr(router_vacantes, "generar_textos_marketing", generar_falso)

    assert client.get(ruta, headers=admin_headers).json() == {"textos": {}}
    generados = client.post(f"/api/vacantes/{vacante['id']}/generar-textos", headers=admin_headers).json()["textos"]
    assert client.get(ruta, headers=admin_headers).json() == {"textos": {}}  # generar no guarda

    editados = {**generados, "whatsapp": "Texto corto editado por RRHH"}
    guardados = client.put(ruta, json={"textos": editados}, headers=admin_headers)
    assert guardados.status_code == 200
    assert client.get(ruta, headers=admin_headers).json() == {"textos": editados}
    assert client.get(f"/api/vacantes/{vacante['id']}", headers=admin_headers).json()["textos_publicacion"] == editados


def test_si_la_ia_falla_responde_502_sin_tocar_la_vacante(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    vacante = _vacante(client, admin_headers, _area(client, admin_headers)["id"])

    async def generar_que_falla(_vacante: Any) -> dict[str, str]:
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(router_vacantes, "generar_textos_marketing", generar_que_falla)

    respuesta = client.post(f"/api/vacantes/{vacante['id']}/generar-textos", headers=admin_headers)
    assert respuesta.status_code == 502
    assert "intenta de nuevo" in respuesta.json()["detail"]
    detalle = client.get(f"/api/vacantes/{vacante['id']}", headers=admin_headers).json()
    assert detalle["estado"] == "borrador" and detalle["updated_at"] == vacante["updated_at"]
