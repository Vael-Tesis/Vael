"""Clave de S3 a partir de la URL guardada en `cv_url` (DEP-C-01): el análisis descarga el CV con
el cliente de S3, porque el bucket de AWS es privado y una URL sin firma responde 403."""
from typing import Any

import pytest

from app.services import aws_services


def test_clave_desde_la_url_de_s3_de_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aws_services.settings, "s3_bucket_name", "vael-storage")
    url = "https://vael-storage.s3.us-east-1.amazonaws.com/cvs/t1/v1/abc_CV Ana.pdf"
    assert aws_services.clave_desde_url(url) == "cvs/t1/v1/abc_CV Ana.pdf"


def test_clave_desde_la_url_del_s3_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aws_services.settings, "s3_bucket_name", "vael-storage")
    url = "http://localhost:9090/vael-storage/cvs/t1/v1/abc_CV%20Ana.pdf"
    assert aws_services.clave_desde_url(url) == "cvs/t1/v1/abc_CV Ana.pdf"


def test_las_credenciales_temporales_incluyen_el_token_de_sesion(monkeypatch: pytest.MonkeyPatch) -> None:
    """En la Lambda, AWS entrega clave, secreto y token de sesión: los tres deben llegar al cliente
    (sin el token, S3 respondía InvalidAccessKeyId en el despliegue del 2026-11-08)."""

    vistos: dict[str, Any] = {}

    class SesionFalsa:
        def __init__(self, **kwargs: Any) -> None:
            vistos.update(kwargs)

        def client(self, *_a: Any, **_k: Any) -> None:
            return None

    monkeypatch.setattr(aws_services.settings, "s3_endpoint_url", None)
    monkeypatch.setattr(aws_services.settings, "aws_access_key_id", "ASIA-temporal")
    monkeypatch.setattr(aws_services.settings, "aws_secret_access_key", "secreto")
    monkeypatch.setattr(aws_services.settings, "aws_session_token", "token-de-sesion")
    monkeypatch.setattr(aws_services.aioboto3, "Session", SesionFalsa)

    aws_services._cliente("s3")

    assert vistos["aws_session_token"] == "token-de-sesion"
