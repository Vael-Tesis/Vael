"""Pruebas del endpoint de salud."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_devuelve_ok() -> None:
    """GET /health debe responder 200 con {"status": "ok"}."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
