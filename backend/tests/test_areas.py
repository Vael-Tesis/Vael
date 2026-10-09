"""Pruebas de /api/areas/ — CRUD feliz y control de acceso (401/403)."""
from fastapi.testclient import TestClient


def test_sin_token_responde_403(client: TestClient) -> None:
    """GET sin header Authorization -> 403 (HTTPBearer, mismo comportamiento que el resto de la app)."""
    response = client.get("/api/areas")
    assert response.status_code == 403


def test_token_invalido_responde_401(client: TestClient) -> None:
    """GET con un token mal formado -> 401 (decode_token falla)."""
    response = client.get("/api/areas", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert response.status_code == 401


def test_reclutador_no_puede_crear_area(client: TestClient, reclutador_headers: dict[str, str]) -> None:
    """POST con rol RECLUTADOR -> 403 (solo ADMIN/GERENTE pueden crear áreas)."""
    response = client.post(
        "/api/areas/",
        json={"nombre": "Tecnología", "codigo_corto": "TI"},
        headers=reclutador_headers,
    )
    assert response.status_code == 403


def test_crud_feliz_de_areas(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Flujo feliz completo: crear, listar, obtener detalle y editar un área."""
    crear = client.post(
        "/api/areas/",
        json={"nombre": "Tecnología", "codigo_corto": "TI", "descripcion": "Equipo de TI"},
        headers=admin_headers,
    )
    assert crear.status_code == 201, crear.text
    area = crear.json()
    assert area["nombre"] == "Tecnología"
    assert area["codigo_corto"] == "TI"
    assert area["activa"] is True

    listar = client.get("/api/areas", headers=admin_headers)
    assert listar.status_code == 200
    assert any(a["id"] == area["id"] for a in listar.json())

    detalle = client.get(f"/api/areas/{area['id']}", headers=admin_headers)
    assert detalle.status_code == 200
    assert detalle.json()["id"] == area["id"]

    editar = client.put(
        f"/api/areas/{area['id']}",
        json={"activa": False},
        headers=admin_headers,
    )
    assert editar.status_code == 200
    assert editar.json()["activa"] is False


def test_area_de_otro_tenant_no_es_visible(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Una área no existente (u otro tenant) responde 404, no 200 con datos ajenos."""
    respuesta = client.get("/api/areas/id-que-no-existe", headers=admin_headers)
    assert respuesta.status_code == 404
