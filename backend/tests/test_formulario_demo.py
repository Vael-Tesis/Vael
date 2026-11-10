"""Lambda del formulario de demo de la landing (DEP-C-07, DEC-027).

El código vive inline en `infra/aws/base.yaml` (CloudFormation lo empaqueta como `index.py`).
La prueba lo extrae entre las marcas INICIO-HANDLER y FIN-HANDLER y lo ejecuta con un cliente
de SES falso: nada sale a AWS.
"""
import json
import sys
import textwrap
import types
from pathlib import Path
from typing import Any

import pytest

PLANTILLA = Path(__file__).resolve().parents[2] / "infra" / "aws" / "base.yaml"
ORIGEN = "https://www.vael.work"


def _codigo_del_handler() -> str:
    texto = PLANTILLA.read_text(encoding="utf-8")
    inicio = texto.index("# INICIO-HANDLER")
    fin = texto.index("# FIN-HANDLER")
    return textwrap.dedent(texto[texto.rindex("\n", 0, inicio) + 1 : fin])


class SesFalso:
    def __init__(self, falla: bool = False) -> None:
        self.enviados: list[dict[str, Any]] = []
        self.falla = falla

    def send_email(self, **kwargs: Any) -> dict[str, str]:
        if self.falla:
            raise RuntimeError("MessageRejected")
        self.enviados.append(kwargs)
        return {"MessageId": "x"}


@pytest.fixture
def modulo(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    ses = SesFalso()
    boto3_falso = types.SimpleNamespace(client=lambda _servicio: ses)
    monkeypatch.setitem(sys.modules, "boto3", boto3_falso)
    monkeypatch.setenv("CORREO_CONTACTO", "contacto@vael.work")
    monkeypatch.setenv("ORIGENES", "https://www.vael.work,https://vael.work")
    mod = types.ModuleType("index")
    exec(compile(_codigo_del_handler(), "index.py", "exec"), mod.__dict__)  # noqa: S102 — código propio del repo
    mod.ses_falso = ses  # type: ignore[attr-defined]
    return mod


def _evento(cuerpo: Any, origen: str = ORIGEN) -> dict[str, Any]:
    return {"headers": {"Origin": origen}, "body": json.dumps(cuerpo)}


def test_cabe_en_el_codigo_inline_de_cloudformation() -> None:
    assert len(_codigo_del_handler()) < 4096


def test_envia_la_confirmacion_al_visitante_y_el_aviso_al_equipo(modulo: types.ModuleType) -> None:
    respuesta = modulo.handler(_evento({"correo": "ana@empresa.pe"}), None)

    assert respuesta["statusCode"] == 200
    visitante, equipo = modulo.ses_falso.enviados
    assert visitante["Destination"] == {"ToAddresses": ["ana@empresa.pe"]}
    assert visitante["FromEmailAddress"] == "VAEL <contacto@vael.work>"
    assert visitante["ReplyToAddresses"] == ["contacto@vael.work"]
    texto = visitante["Content"]["Simple"]["Body"]["Text"]["Data"]
    assert "la IA recomienda y tu equipo de RRHH decide" in texto
    assert "Html" in visitante["Content"]["Simple"]["Body"]
    assert equipo["Destination"] == {"ToAddresses": ["contacto@vael.work"]}
    assert equipo["ReplyToAddresses"] == ["ana@empresa.pe"]


@pytest.mark.parametrize(
    ("evento", "codigo"),
    [
        (_evento({"correo": "ana@empresa.pe"}, origen="https://otro.sitio"), 403),
        ({"headers": {"origin": ORIGEN}, "body": "no es json"}, 400),
        (_evento(["lista"]), 400),
        (_evento({"correo": "sin-arroba"}), 422),
        (_evento({"correo": "a@b.pe, c@d.pe"}), 422),
        (_evento({"correo": "x" * 250 + "@empresa.pe"}), 422),
    ],
    ids=["otro-origen", "cuerpo-invalido", "no-objeto", "sin-arroba", "dos-correos", "muy-largo"],
)
def test_rechaza_sin_enviar_nada(modulo: types.ModuleType, evento: dict[str, Any], codigo: int) -> None:
    assert modulo.handler(evento, None)["statusCode"] == codigo
    assert modulo.ses_falso.enviados == []


def test_el_campo_trampa_responde_ok_sin_enviar(modulo: types.ModuleType) -> None:
    respuesta = modulo.handler(_evento({"correo": "bot@spam.pe", "sitio": "https://spam"}), None)
    assert respuesta["statusCode"] == 200
    assert modulo.ses_falso.enviados == []


def test_limita_los_envios_por_ventana(modulo: types.ModuleType) -> None:
    for i in range(modulo.LIMITE):
        assert modulo.handler(_evento({"correo": f"p{i}@empresa.pe"}), None)["statusCode"] == 200
    assert modulo.handler(_evento({"correo": "extra@empresa.pe"}), None)["statusCode"] == 429


def test_si_ses_rechaza_responde_502(modulo: types.ModuleType) -> None:
    modulo._ses[:] = [SesFalso(falla=True)]
    assert modulo.handler(_evento({"correo": "ana@empresa.pe"}), None)["statusCode"] == 502
