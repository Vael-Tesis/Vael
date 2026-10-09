"""Pruebas de /api/plantillas/ — CRUD feliz y control de acceso (401/403)."""
from fastapi.testclient import TestClient


def test_sin_token_responde_403(client: TestClient) -> None:
    """GET sin header Authorization -> 403."""
    response = client.get("/api/plantillas")
    assert response.status_code == 403


def test_reclutador_no_puede_crear_plantilla(client: TestClient, reclutador_headers: dict[str, str]) -> None:
    """POST con rol RECLUTADOR -> 403 (solo ADMIN/GERENTE administran plantillas)."""
    response = client.post(
        "/api/plantillas/",
        json={"nombre": "Entrevista técnica"},
        headers=reclutador_headers,
    )
    assert response.status_code == 403


def test_crud_feliz_de_plantillas_y_dimensiones(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Flujo feliz: crear plantilla con dimensiones iniciales, listar, editar, agregar/editar/borrar dimensión."""
    crear = client.post(
        "/api/plantillas/",
        json={
            "nombre": "Entrevista técnica",
            "descripcion": "Evalúa comunicación y profundidad técnica",
            "dimensiones": [
                {"nombre": "Claridad", "peso": 0.5},
                {"nombre": "Precisión técnica", "peso": 0.5},
            ],
        },
        headers=admin_headers,
    )
    assert crear.status_code == 201, crear.text
    plantilla = crear.json()
    assert plantilla["nombre"] == "Entrevista técnica"
    assert len(plantilla["dimensiones"]) == 2

    listar = client.get("/api/plantillas", headers=admin_headers)
    assert listar.status_code == 200
    assert any(p["id"] == plantilla["id"] for p in listar.json())

    detalle = client.get(f"/api/plantillas/{plantilla['id']}", headers=admin_headers)
    assert detalle.status_code == 200
    assert len(detalle.json()["dimensiones"]) == 2

    editar = client.put(
        f"/api/plantillas/{plantilla['id']}",
        json={"activa": False},
        headers=admin_headers,
    )
    assert editar.status_code == 200
    assert editar.json()["activa"] is False

    agregar_dim = client.post(
        f"/api/plantillas/{plantilla['id']}/dimensiones",
        json={"nombre": "Seguridad", "peso": 0.2},
        headers=admin_headers,
    )
    assert agregar_dim.status_code == 201, agregar_dim.text
    dimension_id = agregar_dim.json()["id"]

    editar_dim = client.put(
        f"/api/plantillas/{plantilla['id']}/dimensiones/{dimension_id}",
        json={"peso": 0.3},
        headers=admin_headers,
    )
    assert editar_dim.status_code == 200
    assert editar_dim.json()["peso"] == 0.3

    borrar_dim = client.delete(
        f"/api/plantillas/{plantilla['id']}/dimensiones/{dimension_id}",
        headers=admin_headers,
    )
    assert borrar_dim.status_code == 200
    assert borrar_dim.json() == {"detail": "Dimensión eliminada"}

    borrar_dim_de_nuevo = client.delete(
        f"/api/plantillas/{plantilla['id']}/dimensiones/{dimension_id}",
        headers=admin_headers,
    )
    assert borrar_dim_de_nuevo.status_code == 404
