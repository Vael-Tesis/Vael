"""Exporta el contrato OpenAPI del backend para generar el cliente tipado del frontend (DEC-008).

Uso:

    python -m app.scripts.exportar_openapi [ruta]   # por defecto, frontend/openapi.json

No levanta el servidor ni se conecta a la base de datos: genera el esquema desde la app. Las
claves se ordenan para que el archivo versionado solo cambie cuando cambia el contrato.
Después, en frontend/: `npm run api:generar`. El CI falla si cualquiera de los dos
archivos generados quedó desactualizado (DEV-C-09).
"""
import json
import sys
from pathlib import Path

from app.main import app

DESTINO_POR_DEFECTO = Path(__file__).resolve().parents[3] / "frontend" / "openapi.json"


def exportar(destino: Path = DESTINO_POR_DEFECTO) -> Path:
    contenido = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    destino.write_text(contenido, encoding="utf-8", newline="\n")
    return destino


if __name__ == "__main__":
    ruta = exportar(Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINO_POR_DEFECTO)
    print(f"OpenAPI exportado en {ruta}", file=sys.stderr)
