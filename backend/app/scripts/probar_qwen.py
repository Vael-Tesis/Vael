"""Prueba la conexión con el Qwen del instituto y muestra sus modelos (DEC-025, DEV-C-15).

Uso (en backend/, con QWEN_BASE_URL y QWEN_API_KEY en el .env; QWEN_MODEL puede faltar):

    python -m app.scripts.probar_qwen

1. Lista los modelos que expone el servidor (`GET /models`).
2. Si hay QWEN_MODEL, hace una llamada de prueba que debe devolver JSON y mide su duración.

No imprime la clave.
"""
import asyncio
import sys
import time

from app.core.config import settings
from app.core.qwen import consultar_qwen_json, listar_modelos


async def probar() -> int:
    if not settings.qwen_base_url:
        print("Falta QWEN_BASE_URL en backend/.env", file=sys.stderr)
        return 1
    print(f"Servidor: {settings.qwen_base_url}")
    try:
        modelos = await listar_modelos()
    except Exception as exc:  # noqa: BLE001 - se informa cualquier falla de conexión
        print(f"No se pudieron listar los modelos: {exc!r}", file=sys.stderr)
        return 1
    print("Modelos disponibles:", ", ".join(modelos) or "(ninguno)")

    if not settings.qwen_model:
        print("Copia el ID del modelo en QWEN_MODEL y vuelve a ejecutar para la llamada de prueba.")
        return 0
    inicio = time.perf_counter()
    respuesta = await consultar_qwen_json('Devuelve exactamente este JSON: {"estado": "ok", "numero": 7}')
    print(f"Respuesta de {settings.qwen_model} en {time.perf_counter() - inicio:.1f} s: {respuesta}")
    return 0 if respuesta.get("estado") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(probar()))
