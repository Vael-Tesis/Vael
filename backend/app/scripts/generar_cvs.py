"""Genera los 20 CV ficticios del doc 13 como PDF en backend/seeds/cvs/ (DEV-C-03).

Uso:

    python -m app.scripts.generar_cvs

Los textos viven en backend/seeds/cvs_texto/*.txt; los PDF se regeneran siempre igual, por
eso no se versionan. Dos casos se construyen a propósito sin texto utilizable:
- CV-TI-11: PDF "escaneado", solo una imagen y ningún texto extraíble (revisión manual).
- CV-TI-12: PDF dañado, truncado a la mitad (reporte de fallidos, RF-A-09).

El PDF se escribe a mano (PDF 1.4, Helvetica, WinAnsiEncoding) para no agregar una
dependencia solo por las semillas.
"""
import sys
from pathlib import Path

DIRECTORIO_SEMILLAS = Path(__file__).resolve().parents[2] / "seeds"
DIRECTORIO_TEXTOS = DIRECTORIO_SEMILLAS / "cvs_texto"
DIRECTORIO_PDF = DIRECTORIO_SEMILLAS / "cvs"

CV_ESCANEADO = "CV-TI-11"
CV_DANADO = "CV-TI-12"

_LINEAS_POR_PAGINA = 48
_INTERLINEADO = 14
_MARGEN_SUPERIOR = 800


def _escapar(linea: str) -> bytes:
    """Texto de una línea como cadena literal de PDF en WinAnsiEncoding (cp1252)."""
    texto = linea.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return texto.encode("cp1252", errors="replace")


def _documento(contenidos: list[bytes], recursos: bytes) -> bytes:
    """Arma un PDF con una página por flujo de contenido."""
    objetos: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    paginas: list[int] = []
    for contenido in contenidos:
        numero_contenido = len(objetos) + 2
        objetos.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources "
            + recursos
            + b" /Contents "
            + str(numero_contenido).encode()
            + b" 0 R >>"
        )
        paginas.append(len(objetos))
        objetos.append(b"<< /Length " + str(len(contenido)).encode() + b" >>\nstream\n" + contenido + b"\nendstream")
    kids = b" ".join(f"{n} 0 R".encode() for n in paginas)
    objetos[1] = b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(paginas)).encode() + b" >>"

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones: list[int] = []
    for indice, objeto in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += f"{indice} 0 obj\n".encode() + objeto + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for posicion in posiciones:
        salida += f"{posicion:010d} 00000 n \n".encode()
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
    return bytes(salida)


def pdf_de_texto(texto: str) -> bytes:
    """PDF con el texto, una línea por renglón, paginado."""
    lineas = texto.splitlines() or [""]
    contenidos = []
    for inicio in range(0, len(lineas), _LINEAS_POR_PAGINA):
        flujo = bytearray(b"BT /F1 10 Tf 50 " + str(_MARGEN_SUPERIOR).encode() + b" Td ")
        flujo += str(_INTERLINEADO).encode() + b" TL "
        for linea in lineas[inicio : inicio + _LINEAS_POR_PAGINA]:
            flujo += b"(" + _escapar(linea) + b") Tj T* "
        flujo += b"ET"
        contenidos.append(bytes(flujo))
    recursos = b"<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> >> >>"
    return _documento(contenidos, recursos)


def pdf_escaneado() -> bytes:
    """PDF de una página con solo una imagen en escala de grises: nada de texto que extraer."""
    lado = 16
    pixeles = bytes((x * 7 + y * 11) % 256 for y in range(lado) for x in range(lado)).hex().encode()
    contenido = (
        b"q 495 0 0 742 50 50 cm BI /W " + str(lado).encode() + b" /H " + str(lado).encode()
        + b" /CS /G /BPC 8 /F /AHx ID " + pixeles + b"> EI Q"
    )
    return _documento([contenido], b"<< >>")


def pdf_danado(texto: str) -> bytes:
    """PDF truncado a la mitad, sin tabla de referencias ni fin de archivo."""
    completo = pdf_de_texto(texto)
    return completo[: len(completo) // 2]


def generar(destino: Path = DIRECTORIO_PDF) -> list[Path]:
    """Genera los 20 PDF y retorna sus rutas."""
    destino.mkdir(parents=True, exist_ok=True)
    textos = {ruta.stem: ruta.read_text(encoding="utf-8") for ruta in sorted(DIRECTORIO_TEXTOS.glob("*.txt"))}
    archivos = {codigo: pdf_de_texto(texto) for codigo, texto in textos.items()}
    archivos[CV_ESCANEADO] = pdf_escaneado()
    archivos[CV_DANADO] = pdf_danado(textos["CV-TI-01"])

    rutas = []
    for codigo, contenido in sorted(archivos.items()):
        ruta = destino / f"{codigo}.pdf"
        ruta.write_bytes(contenido)
        rutas.append(ruta)
    return rutas


if __name__ == "__main__":
    generados = generar()
    print(f"{len(generados)} CV generados en {DIRECTORIO_PDF}", file=sys.stderr)
