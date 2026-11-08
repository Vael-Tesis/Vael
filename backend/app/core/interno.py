"""Firma HMAC-SHA256 de las entregas de las Lambdas al backend (DEC-018, DEV-C-13 · HU-23).

Las Lambdas no acceden a la base de datos: calculan con Gemini y entregan el resultado por
`/api/interno/...`. Esa ruta es alcanzable a través de CloudFront y del ALB, así que cada
entrega lleva una marca de tiempo y la firma HMAC-SHA256 de `"<marca>." + cuerpo` con el
secreto compartido (`INTERNAL_SERVICE_KEY`, en Secrets Manager). El backend rechaza una firma
inválida y una marca con más de 5 minutos de diferencia (protección contra reenvíos).
"""
import hashlib
import hmac
import time

from app.core.config import settings

CABECERA_MARCA = "X-Vael-Marca-Tiempo"
CABECERA_FIRMA = "X-Vael-Firma"
VENTANA_SEGUNDOS = 300


def _firma(cuerpo: bytes, marca: str, secreto: str) -> str:
    return hmac.new(secreto.encode(), marca.encode() + b"." + cuerpo, hashlib.sha256).hexdigest()


def firmar(cuerpo: bytes, marca_tiempo: int | None = None) -> tuple[str, str]:
    """Devuelve (marca, firma) para enviar en las cabeceras de la entrega. La usan las Lambdas."""
    if not settings.internal_service_key:
        raise RuntimeError("Falta INTERNAL_SERVICE_KEY: no se puede firmar la entrega")
    marca = str(int(time.time()) if marca_tiempo is None else marca_tiempo)
    return marca, _firma(cuerpo, marca, settings.internal_service_key)


def verificar_firma(cuerpo: bytes, marca_tiempo: str | None, firma: str | None, ahora: float | None = None) -> bool:
    """True solo si la firma corresponde al cuerpo y la marca está dentro de la ventana de 5 minutos."""
    if not settings.internal_service_key or not marca_tiempo or not firma:
        return False
    try:
        marca = int(marca_tiempo)
    except ValueError:
        return False
    if abs((time.time() if ahora is None else ahora) - marca) > VENTANA_SEGUNDOS:
        return False
    esperada = _firma(cuerpo, str(marca), settings.internal_service_key)
    return hmac.compare_digest(esperada, firma)
