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
    """Flujo feliz: crear con dimensiones que suman 100, listar, editar y reemplazar dimensiones."""
    crear = client.post(
        "/api/plantillas/",
        json={
            "nombre": "Entrevista técnica",
            "descripcion": "Evalúa comunicación y profundidad técnica",
            "dimensiones": [
                {"nombre": "Claridad", "peso": 50},
                {"nombre": "Precisión técnica", "peso": 50},
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

    editar = client.put(f"/api/plantillas/{plantilla['id']}", json={"activa": False}, headers=admin_headers)
    assert editar.status_code == 200
    assert editar.json()["activa"] is False
    assert len(editar.json()["dimensiones"]) == 2  # sin `dimensiones`, no se tocan

    # Cambiar varios pesos a la vez: se reemplaza el conjunto completo
    reemplazar = client.put(
        f"/api/plantillas/{plantilla['id']}",
        json={"dimensiones": [
            {"nombre": "Claridad", "peso": 40},
            {"nombre": "Precisión técnica", "peso": 40},
            {"nombre": "Seguridad", "peso": 20},
        ]},
        headers=admin_headers,
    )
    assert reemplazar.status_code == 200, reemplazar.text
    dimensiones = {d["nombre"]: d for d in reemplazar.json()["dimensiones"]}
    assert {n: d["peso"] for n, d in dimensiones.items()} == {"Claridad": 40, "Precisión técnica": 40, "Seguridad": 20}

    # Editar sin cambiar el peso siempre se puede
    renombrar = client.put(
        f"/api/plantillas/{plantilla['id']}/dimensiones/{dimensiones['Seguridad']['id']}",
        json={"nombre": "Seguridad y confianza"},
        headers=admin_headers,
    )
    assert renombrar.status_code == 200
    assert renombrar.json()["nombre"] == "Seguridad y confianza"


def test_los_pesos_deben_sumar_100(client: TestClient, admin_headers: dict[str, str]) -> None:
    """CA-06: una plantilla cuyos pesos no suman 100 se rechaza con un mensaje claro."""
    invalida = client.post(
        "/api/plantillas/",
        json={"nombre": "Inválida", "dimensiones": [{"nombre": "A", "peso": 60}, {"nombre": "B", "peso": 30}]},
        headers=admin_headers,
    )
    assert invalida.status_code == 422
    assert invalida.json()["detail"] == "Los pesos de las dimensiones deben sumar 100; ahora suman 90"

    sin_dimensiones = client.post("/api/plantillas/", json={"nombre": "Vacía"}, headers=admin_headers)
    assert sin_dimensiones.status_code == 422

    plantilla = client.post(
        "/api/plantillas/",
        json={"nombre": "Válida", "dimensiones": [{"nombre": "A", "peso": 70}, {"nombre": "B", "peso": 30}]},
        headers=admin_headers,
    ).json()
    ruta = f"/api/plantillas/{plantilla['id']}"
    dimension_a = next(d for d in plantilla["dimensiones"] if d["nombre"] == "A")

    assert client.post(f"{ruta}/dimensiones", json={"nombre": "C", "peso": 10}, headers=admin_headers).status_code == 422
    assert client.put(f"{ruta}/dimensiones/{dimension_a['id']}", json={"peso": 60}, headers=admin_headers).status_code == 422
    assert client.delete(f"{ruta}/dimensiones/{dimension_a['id']}", headers=admin_headers).status_code == 422
    assert client.put(ruta, json={"dimensiones": [{"nombre": "A", "peso": 99}]}, headers=admin_headers).status_code == 422
    # Nada cambió
    assert sorted(d["peso"] for d in client.get(ruta, headers=admin_headers).json()["dimensiones"]) == [30, 70]
