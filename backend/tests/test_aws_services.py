"""Clave de S3 a partir de la URL guardada en `cv_url` (DEP-C-01): el análisis descarga el CV con
el cliente de S3, porque el bucket de AWS es privado y una URL sin firma responde 403."""
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
