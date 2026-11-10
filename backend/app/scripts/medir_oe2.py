"""Mide el OE2 (doc 14, TST-A-05 y TST-A-06): consistencia del análisis de CV, con Gemini y con Qwen.

Analiza CV-TI-01, CV-TI-04 y CV-TI-07 (doc 13: alto, límite y bajo) contra TI-2026-001,
10 veces cada uno, con la misma función, el mismo prompt y la misma configuración de
generación que usa el sistema en producción (`app.services.analisis_cv`,
`app.core.gemini.consultar_gemini_json`) — sin bajar la temperatura ni cambiar ningún
parámetro: el OE2 mide la consistencia del sistema tal como funciona, no de una
configuración aparte para la medición.

No forma parte del CI ni de pytest: hace 30 llamadas reales al modelo. Uso:

    python -m app.scripts.medir_oe2 --proveedor gemini
    python -m app.scripts.medir_oe2 --proveedor qwen

**Dos registros separados (DEC-026, propuesta):** cada proveedor tiene su carpeta en
`docs/metricas/oe2_<proveedor>/`, con su corrida completa (`consistencia.json`), sus intentos
fallidos (`intento_NN_<motivo>.json`) y sus partes (`partes/`). Uno nunca reemplaza al otro.
Gemini usa `GEMINI_API_KEY`; Qwen, el modelo compatible con OpenAI de `QWEN_BASE_URL`,
`QWEN_MODEL` y `QWEN_API_KEY`. Cada ejecución registra el proveedor, el modelo y, en Qwen, el
servidor.

Por partes (el plan gratuito de Gemini permite 20 solicitudes por día y por modelo, doc 04):
cada parte mide un CV completo (sus 10 ejecuciones) y, cuando están los tres, se unen en la
corrida completa. Las ejecuciones no cambian: mismo modelo, prompt y configuración en cada parte.

    python -m app.scripts.medir_oe2 --proveedor gemini --cv CV-TI-01     # un día
    python -m app.scripts.medir_oe2 --proveedor gemini --cv CV-TI-04 --cv CV-TI-07   # otro día
    python -m app.scripts.medir_oe2 --proveedor gemini --unir

Las claves nunca se imprimen ni se guardan en ningún archivo. Si una llamada falla después de
los reintentos del cliente (429/503/504), esa ejecución queda registrada como fallida — no se
repite en silencio ni se reemplaza por otra.
"""
import argparse
import asyncio
import json
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.core.gemini import _configuracion_json, consultar_gemini_json
from app.core.qwen import INSTRUCCION_SISTEMA, consultar_qwen_json, qwen_configurado
from app.models.area import Area
from app.models.vacante import Vacante
from app.scripts import semillas
from app.services.analisis_cv import (
    _como_clasificacion,
    _validar_y_sumar_desglose,
    construir_prompt_analisis,
    datos_prompt_vacante,
    extraer_texto_pdf,
)

RAIZ = Path(__file__).resolve().parents[3]
DIRECTORIO_CVS = Path(__file__).resolve().parents[2] / "seeds" / "cvs"
DIRECTORIO_METRICAS = RAIZ / "docs" / "metricas"
PROVEEDORES = ("gemini", "qwen")  # DEC-026: un registro por proveedor
_PATRON_INTENTO = re.compile(r"^intento_(\d+)_.*\.json$")


def directorio_registro(proveedor: str) -> Path:
    """Carpeta del registro del OE2 de ese proveedor (DEC-026)."""
    return DIRECTORIO_METRICAS / f"oe2_{proveedor}"


def salida_corrida_completa(proveedor: str) -> Path:
    """Reservada a una corrida completa (0 ejecuciones fallidas): un intento con fallas nunca
    escribe aquí, para no confundirse con la medición real del OE2."""
    return directorio_registro(proveedor) / "consistencia.json"


def directorio_partes(proveedor: str) -> Path:
    """Partes exitosas de una corrida por partes: una por CV, sin fallas (ver --cv y --unir)."""
    return directorio_registro(proveedor) / "partes"

CVS = ["CV-TI-01", "CV-TI-04", "CV-TI-07"]
EJECUCIONES_POR_CV = 10
# Pausa entre llamadas exitosas para no saturar la cuota (además del backoff ante 429/503/504
# que ya tiene consultar_gemini_json); no es un parámetro de generación, no afecta al OE2.
ESPERA_ENTRE_LLAMADAS_SEGUNDOS = 3.0
META_DESVIACION_ESTANDAR = 5.0


@dataclass
class Ejecucion:
    cv: str
    numero: int
    fecha_hora_utc: str
    duracion_ms: float | None
    modelo: str
    parametros_generacion: dict[str, Any]
    score_cv: int | None
    clasificacion_ia: str | None
    recomendacion: str  # "avanzar" | "descartar" | "error"
    umbral_score_cv_minimo: float
    error: str | None = None
    proveedor: str = "gemini"


def _vacante_y_area_semillas() -> tuple[Vacante, Area]:
    """Construye en memoria la vacante y el área de TI-2026-001, desde las constantes del
    script de semillas (doc 13) — sin tocar la base de datos: esta medición no persiste nada."""
    area_semilla = next(a for a in semillas.AREAS if a[2] == "TI")
    area = Area(tenant_id="medicion-oe2", nombre=area_semilla[1], codigo_corto=area_semilla[2], instruccion_ia=area_semilla[3])

    vacante_semilla = next(v for v in semillas.VACANTES if v.codigo == "TI-2026-001")
    vacante = Vacante(
        tenant_id="medicion-oe2", area_id=area.id, codigo=vacante_semilla.codigo, titulo=vacante_semilla.titulo,
        nivel_experiencia=vacante_semilla.nivel, estado=vacante_semilla.estado,
        requisitos=vacante_semilla.requisitos, habilidades=list(vacante_semilla.habilidades),
    )
    return vacante, area


def _servidor_qwen() -> str:
    """Solo el host del servidor de Qwen (sin ruta ni credenciales), para el registro."""
    return urlparse(settings.qwen_base_url).hostname or "desconocido"


def _modelo(proveedor: str) -> str:
    return settings.gemini_model if proveedor == "gemini" else settings.qwen_model


def _parametros_qwen() -> dict[str, Any]:
    """Los parámetros que envía `consultar_qwen_json`, los mismos que usa el sistema con Qwen."""
    return {
        "api": "chat/completions compatible con OpenAI",
        "servidor": _servidor_qwen(),
        "max_tokens": 4096,
        "instruccion_sistema": INSTRUCCION_SISTEMA,
        "temperature": "valor por defecto del servidor (no se fija, igual que en producción)",
    }


def _parametros_generacion() -> dict[str, Any]:
    """Los mismos parámetros de generación que usa `consultar_gemini_json` en producción,
    para que el registro de cada ejecución los deje explícitos (OE2, doc 14). No se cambia
    ninguno para la medición: ni siquiera la temperatura, que Gemini deja en su valor por
    defecto porque `_configuracion_json()` no la fija."""
    configuracion = _configuracion_json()
    return {
        "response_mime_type": configuracion.response_mime_type,
        "automatic_function_calling_disabled": configuracion.automatic_function_calling.disable,
        "temperature": "valor por defecto de Gemini (no se fija, igual que en producción)",
    }


async def _ejecutar_una_vez(cv: str, numero: int, prompt: str, umbral: float, proveedor: str) -> Ejecucion:
    parametros = _parametros_generacion() if proveedor == "gemini" else _parametros_qwen()
    modelo = _modelo(proveedor)
    inicio = time.perf_counter()
    try:
        if proveedor == "gemini":
            # Medición de Gemini: sin pasar al respaldo (DEC-025), para no mezclar modelos
            resultado = await consultar_gemini_json(prompt, permitir_respaldo=False)
        else:
            # Directo a Qwen (DEC-026), sin pasar por Gemini
            resultado = await consultar_qwen_json(prompt)
        # DEC-024: la misma validación de producción — un desglose inválido es una ejecución
        # fallida, igual que cualquier otro error de consultar_gemini_json.
        score, _desglose = _validar_y_sumar_desglose(resultado.get("criterios"))
    except Exception as exc:  # noqa: BLE001 — se registra tal cual, no se reintenta en silencio
        duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
        print(f"  [{cv} #{numero}] FALLÓ tras los reintentos de consultar_gemini_json: {exc!r}", file=sys.stderr)
        return Ejecucion(
            cv=cv, numero=numero, fecha_hora_utc=datetime.now(timezone.utc).isoformat(), duracion_ms=duracion_ms,
            modelo=modelo, parametros_generacion=parametros, score_cv=None, clasificacion_ia=None,
            recomendacion="error", umbral_score_cv_minimo=umbral, error=str(exc), proveedor=proveedor,
        )

    duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
    clasificacion = _como_clasificacion(resultado.get("clasificacion"))
    recomendacion = "avanzar" if score >= umbral else "descartar"
    print(f"  [{cv} #{numero}] score={score} clasificacion={clasificacion.value} recomendacion={recomendacion} ({duracion_ms:.0f} ms)")
    return Ejecucion(
        cv=cv, numero=numero, fecha_hora_utc=datetime.now(timezone.utc).isoformat(), duracion_ms=duracion_ms,
        modelo=modelo, parametros_generacion=parametros, score_cv=score,
        clasificacion_ia=clasificacion.value, recomendacion=recomendacion, umbral_score_cv_minimo=umbral,
        proveedor=proveedor,
    )


def _resumen_por_cv(ejecuciones: list[Ejecucion]) -> dict[str, Any]:
    exitosas = [e for e in ejecuciones if e.error is None]
    fallidas = [e for e in ejecuciones if e.error is not None]
    scores = [e.score_cv for e in exitosas if e.score_cv is not None]
    recomendaciones = {e.recomendacion for e in exitosas}

    media = round(statistics.mean(scores), 2) if scores else None
    desviacion = round(statistics.stdev(scores), 2) if len(scores) > 1 else (0.0 if scores else None)

    return {
        "ejecuciones_totales": len(ejecuciones),
        "ejecuciones_exitosas": len(exitosas),
        "ejecuciones_fallidas": len(fallidas),
        "scores": scores,
        "media": media,
        "desviacion_estandar": desviacion,
        "cumple_meta_oe2": (desviacion is not None and desviacion <= META_DESVIACION_ESTANDAR) if desviacion is not None else None,
        "la_recomendacion_cambio_entre_ejecuciones": len(recomendaciones) > 1,  # M-03
        "recomendaciones_vistas": sorted(recomendaciones),
    }


def _motivo_fallo(ejecuciones: list[Ejecucion]) -> str:
    """Un slug corto que describe por qué falló el intento, a partir de los errores
    registrados — para que el nombre del archivo (`intento_NN_<motivo>.json`) ya diga
    algo sin tener que abrirlo."""
    errores = " ".join(e.error for e in ejecuciones if e.error)
    if "RESOURCE_EXHAUSTED" in errores or "429" in errores:
        return "cuota_agotada"
    if "UNAVAILABLE" in errores or "503" in errores:
        return "servicio_no_disponible"
    if "DEADLINE_EXCEEDED" in errores or "504" in errores:
        return "plazo_vencido"
    if "sin respuesta en" in errores:
        return "tiempo_agotado"
    return "fallo_parcial"


def _siguiente_ruta_intento(motivo: str, proveedor: str) -> Path:
    """El próximo `intento_NN_<motivo>.json` del registro de ese proveedor, con NN siguiente al
    último que exista — nunca reutiliza ni sobrescribe el número de un intento anterior."""
    directorio = directorio_registro(proveedor)
    numeros_existentes = [
        int(coincidencia.group(1))
        for archivo in directorio.glob("intento_*.json")
        if (coincidencia := _PATRON_INTENTO.match(archivo.name))
    ]
    siguiente = max(numeros_existentes, default=0) + 1
    return directorio / f"intento_{siguiente:02d}_{motivo}.json"


def _sha_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=RAIZ, text=True).strip()
    except Exception:
        return "desconocido (no se pudo leer con git rev-parse HEAD)"


async def medir(cvs: list[str] | None = None, proveedor: str = "gemini") -> dict[str, Any]:
    if proveedor == "gemini" and not settings.gemini_api_key:
        raise SystemExit("Falta GEMINI_API_KEY en el entorno (backend/.env) — no se mide el OE2 sin una clave real")
    if proveedor == "qwen" and not (qwen_configurado() and settings.qwen_api_key):
        raise SystemExit("Faltan QWEN_BASE_URL, QWEN_MODEL o QWEN_API_KEY en backend/.env — no se mide el OE2 sin una clave real")

    vacante, area = _vacante_y_area_semillas()
    ejecuciones: list[Ejecucion] = []
    cvs = cvs or CVS

    for cv in cvs:
        pdf_bytes = (DIRECTORIO_CVS / f"{cv}.pdf").read_bytes()
        texto_cv = extraer_texto_pdf(pdf_bytes)
        if not texto_cv.strip():
            raise SystemExit(f"{cv}.pdf no tiene texto extraíble — regenera los CV con 'python -m app.scripts.generar_cvs'")
        prompt = construir_prompt_analisis(texto_cv, datos_prompt_vacante(vacante, area))

        print(f"\n{cv} — {EJECUCIONES_POR_CV} ejecuciones contra {vacante.titulo} (umbral score_cv_minimo={vacante.score_cv_minimo})")
        for numero in range(1, EJECUCIONES_POR_CV + 1):
            ejecucion = await _ejecutar_una_vez(cv, numero, prompt, float(vacante.score_cv_minimo), proveedor)
            ejecuciones.append(ejecucion)
            if numero < EJECUCIONES_POR_CV or cv != cvs[-1]:
                await asyncio.sleep(ESPERA_ENTRE_LLAMADAS_SEGUNDOS)

    resumen_por_cv = {cv: _resumen_por_cv([e for e in ejecuciones if e.cv == cv]) for cv in cvs}

    resultado: dict[str, Any] = {
        "_comentario": (
            "Indicador OE2 (doc 14): consistencia del análisis de CV. Meta: desviación estándar "
            "<= 5 puntos sobre 100 en 10 ejecuciones del mismo CV contra la misma vacante, con la "
            "misma función, prompt y configuración de generación que usa el sistema en producción "
            "(sin bajar la temperatura ni cambiar ningún otro parámetro para la medición)."
        ),
        "indicador": "OE2 - consistencia de la calificación automatizada",
        "tarea": "TST-A-05" if proveedor == "gemini" else "TST-A-06",
        "historia": "HU-25",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "sha_commit": _sha_commit(),
        "proveedor": proveedor,
        "modelo": _modelo(proveedor),
        "vacante": vacante.codigo,
        "ejecuciones_por_cv": EJECUCIONES_POR_CV,
        "meta_desviacion_estandar": META_DESVIACION_ESTANDAR,
        "resumen_por_cv": resumen_por_cv,
        "ejecuciones": [asdict(e) for e in ejecuciones],
    }
    if proveedor == "qwen":
        resultado["servidor"] = _servidor_qwen()
        resultado["_comentario"] += (
            f" Registro de Qwen ({_modelo(proveedor)} en {_servidor_qwen()}), separado del de Gemini"
            " (DEC-026, propuesta). El prompt, la vacante, los CV, la validación del desglose y la regla"
            " de recomendación son los del sistema; el resultado describe la consistencia del análisis"
            " con este modelo, no con Gemini."
        )
    return resultado


def unir_partes(proveedor: str) -> dict[str, Any]:
    """Une las partes exitosas de los tres CV en la corrida completa del OE2 de ese proveedor.

    Exige una parte por CV, todas con el mismo modelo y la misma configuración de generación.
    """
    partes: dict[str, dict[str, Any]] = {}
    for cv in CVS:
        candidatas = sorted(directorio_partes(proveedor).glob(f"parte_{cv}_*.json"))
        if not candidatas:
            raise SystemExit(f"Falta la parte de {cv}: ejecuta 'python -m app.scripts.medir_oe2 --proveedor {proveedor} --cv {cv}'")
        partes[cv] = json.loads(candidatas[-1].read_text(encoding="utf-8"))

    modelos = {p["modelo"] for p in partes.values()}
    parametros = {json.dumps(e["parametros_generacion"], sort_keys=True) for p in partes.values() for e in p["ejecuciones"]}
    if len(modelos) > 1 or len(parametros) > 1:
        raise SystemExit(f"Las partes no son comparables: modelos {sorted(modelos)}, {len(parametros)} configuraciones")

    resultado = dict(partes[CVS[0]])
    resultado["fecha_utc"] = datetime.now(timezone.utc).isoformat()
    resultado["sha_commit"] = _sha_commit()
    resultado["resumen_por_cv"] = {cv: partes[cv]["resumen_por_cv"][cv] for cv in CVS}
    resultado["ejecuciones"] = [e for cv in CVS for e in partes[cv]["ejecuciones"]]
    resultado["partes"] = {cv: {"fecha_utc": p["fecha_utc"], "sha_commit": p["sha_commit"]} for cv, p in partes.items()}
    resultado["_comentario"] += (
        " Corrida hecha por partes, un CV por parte (cuota diaria del proveedor); cada parte tiene sus"
        " 10 ejecuciones con el mismo modelo y configuración."
    )
    return resultado


def main() -> int:
    argumentos = argparse.ArgumentParser(description="Mide el OE2 (TST-A-05, TST-A-06)")
    argumentos.add_argument(
        "--proveedor", choices=PROVEEDORES, required=True,
        help="gemini o qwen: cada uno tiene su propio registro en docs/metricas/oe2_<proveedor>/ (DEC-026)",
    )
    argumentos.add_argument("--cv", action="append", choices=CVS, help="Mide solo este CV (una parte)")
    argumentos.add_argument("--unir", action="store_true", help="Une las tres partes en la corrida completa")
    opciones = argumentos.parse_args()
    proveedor = opciones.proveedor

    directorio_registro(proveedor).mkdir(parents=True, exist_ok=True)
    salida = salida_corrida_completa(proveedor)
    if opciones.unir:
        resultado = unir_partes(proveedor)
        salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nCorrida completa (por partes) guardada en {salida}\n")
        _imprimir_resumen(resultado)
        return 0

    resultado = asyncio.run(medir(opciones.cv, proveedor))
    ejecuciones = [Ejecucion(**e) for e in resultado["ejecuciones"]]
    hubo_fallidas = any(r["ejecuciones_fallidas"] > 0 for r in resultado["resumen_por_cv"].values())

    if opciones.cv and not hubo_fallidas:
        directorio_partes(proveedor).mkdir(parents=True, exist_ok=True)
        marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for cv in opciones.cv:
            parte = {**resultado, "resumen_por_cv": {cv: resultado["resumen_por_cv"][cv]},
                     "ejecuciones": [e for e in resultado["ejecuciones"] if e["cv"] == cv]}
            ruta_parte = directorio_partes(proveedor) / f"parte_{cv}_{marca}.json"
            ruta_parte.write_text(json.dumps(parte, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Parte de {cv} guardada en {ruta_parte}")
        _imprimir_resumen(resultado)
        return 0

    if hubo_fallidas:
        ruta = _siguiente_ruta_intento(_motivo_fallo(ejecuciones), proveedor)
        resultado["_comentario"] += (
            " ESTE ARCHIVO ES UN INTENTO FALLIDO (no las 30 ejecuciones exitosas que pide el "
            "CA del OE2): algunas ejecuciones fallaron; 'consistencia.json' queda reservado a "
            "una corrida completa, para no confundir un intento con la medición real."
        )
    else:
        ruta = salida
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nResultado guardado en {ruta}\n")
    _imprimir_resumen(resultado)
    return 1 if hubo_fallidas else 0


def _imprimir_resumen(resultado: dict[str, Any]) -> None:
    print(f"{'CV':<10} {'media':>8} {'desv.est.':>10} {'cumple OE2':>11} {'cambió recomendación':>22} {'fallidas':>9}")
    for cv, resumen in resultado["resumen_por_cv"].items():
        print(
            f"{cv:<10} {resumen['media']!s:>8} {resumen['desviacion_estandar']!s:>10} "
            f"{resumen['cumple_meta_oe2']!s:>11} {resumen['la_recomendacion_cambio_entre_ejecuciones']!s:>22} "
            f"{resumen['ejecuciones_fallidas']!s:>9}"
        )


if __name__ == "__main__":
    sys.exit(main())
