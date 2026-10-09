"""Pruebas de GET /api/entrevista/ — lista de entrevistas del tenant."""
from fastapi.testclient import TestClient


def test_sin_token_responde_403(client: TestClient) -> None:
    """GET sin header Authorization -> 403."""
    response = client.get("/api/entrevista/")
    assert response.status_code == 403


def test_token_invalido_responde_401(client: TestClient) -> None:
    """GET con un token mal formado -> 401."""
    response = client.get("/api/entrevista/", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert response.status_code == 401


def test_lista_vacia_para_tenant_sin_entrevistas(client: TestClient, reclutador_headers: dict[str, str]) -> None:
    """Cualquier usuario autenticado (sin restricción de rol) puede listar; tenant nuevo -> lista vacía."""
    response = client.get("/api/entrevista/", headers=reclutador_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_filtro_por_estado_es_aceptado(client: TestClient, admin_headers: dict[str, str]) -> None:
    """El filtro ?estado= no rompe la consulta y sigue devolviendo una lista (vacía en este tenant)."""
    response = client.get("/api/entrevista/?estado=pendiente", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []
