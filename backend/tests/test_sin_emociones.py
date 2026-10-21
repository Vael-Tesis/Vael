"""Guarda de DEC-001: VAEL no infiere emociones ni analiza el sentimiento del candidato."""
import inspect

from app.services import aws_services


def test_no_existen_funciones_de_emociones_ni_sentimiento() -> None:
    """Las funciones de emociones (Rekognition) y sentimiento (Comprehend) fueron eliminadas."""
    assert not hasattr(aws_services, "detectar_emociones")
    assert not hasattr(aws_services, "analizar_sentimiento")


def test_rekognition_no_pide_atributos_faciales_completos() -> None:
    """Attributes=["ALL"] devuelve emociones; solo se permite la detección básica de rostros."""
    codigo = inspect.getsource(aws_services)
    assert '"ALL"' not in codigo
    assert '_cliente("comprehend")' not in codigo
