"""Pruebas del módulo Holehe tras migrar del parseo de stdout a la API Python.

Las comprobaciones de sitios se sustituyen por corrutinas falsas, de modo que el
volcado de resultados es determinista y no depende ni de la red ni del formato
de impresión de Holehe.
"""

import asyncio

import httpx
import pytest

from modules.holehe_module import HoleheModule


class Recorder:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, text: str) -> None:
        self.lines.append(text)

    @property
    def text(self) -> str:
        return "".join(self.lines)


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


def _resultado(name: str, domain: str, **extra) -> dict:
    base = {
        "name": name,
        "domain": domain,
        "rateLimit": False,
        "exists": False,
        "emailrecovery": None,
        "phoneNumber": None,
        "others": None,
    }
    base.update(extra)
    return base


def _comprobacion(payload: dict):
    """Fabrica una corrutina con la misma firma que un módulo de Holehe."""

    async def check(email, client, out):
        out.append(payload)

    check.__name__ = payload["name"]
    return check


def _patch_websites(monkeypatch, funciones) -> None:
    monkeypatch.setattr(
        "modules.holehe_module._discover_websites", lambda: list(funciones)
    )


def _patch_enrichment(monkeypatch) -> None:
    """Neutraliza las consultas a XposedOrNot y Google."""

    async def _noop(self, email, callback, resultados):
        return None

    monkeypatch.setattr(HoleheModule, "_analizar_brechas_libre", _noop)
    monkeypatch.setattr(HoleheModule, "_analizar_perfil_google", _noop)


# ---------------------------------------------------------------- salud


def test_check_health_detecta_la_libreria() -> None:
    assert HoleheModule().check_health() == ("ok", "holehe_ok")


def test_check_health_sin_libreria(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("holehe"):
            raise ImportError("simulado")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert HoleheModule().check_health() == ("error", "holehe_missing")


# ---------------------------------------------------------------- entrada


@pytest.mark.asyncio
@pytest.mark.parametrize("invalido", ["no-es-un-correo", "", "arroba@", "@dominio.com"])
async def test_rechaza_entradas_que_no_son_correos(
    monkeypatch, recorder, invalido: str
) -> None:
    """Antes se lanzaba el escaneo completo contra cualquier cadena."""
    _patch_enrichment(monkeypatch)
    result = await HoleheModule().run(invalido, recorder)

    assert result["status"] == "error"
    assert result["error"] == "invalid_email"
    assert "correo" in recorder.text


# ---------------------------------------------------------------- volcado


@pytest.mark.asyncio
async def test_reporta_solo_los_sitios_con_registro(monkeypatch, recorder) -> None:
    _patch_enrichment(monkeypatch)
    _patch_websites(
        monkeypatch,
        [
            _comprobacion(_resultado("github", "github.com", exists=True)),
            _comprobacion(_resultado("spotify", "spotify.com", exists=True)),
            _comprobacion(_resultado("twitter", "twitter.com", exists=False)),
        ],
    )

    result = await HoleheModule().run("alguien@example.com", recorder)

    assert result["sitios_detectados"] == ["github.com", "spotify.com"]
    assert "github.com" in recorder.text
    assert "twitter.com" not in recorder.text


@pytest.mark.asyncio
async def test_expone_los_datos_de_recuperacion(monkeypatch, recorder) -> None:
    """El parseo de stdout descartaba estos campos; la API sí los entrega."""
    _patch_enrichment(monkeypatch)
    _patch_websites(
        monkeypatch,
        [
            _comprobacion(
                _resultado(
                    "ebay",
                    "ebay.com",
                    exists=True,
                    emailrecovery="a***@gmail.com",
                    phoneNumber="+34 6## ### #84",
                )
            )
        ],
    )

    result = await HoleheModule().run("alguien@example.com", recorder)

    assert "a***@gmail.com" in recorder.text
    assert "+34 6## ### #84" in recorder.text
    assert result["detalles"][0]["emailrecovery"] == "a***@gmail.com"


@pytest.mark.asyncio
async def test_informa_de_los_servicios_limitados(monkeypatch, recorder) -> None:
    """El escaneo antiguo filtraba estas líneas y daba el resultado por completo."""
    _patch_enrichment(monkeypatch)
    _patch_websites(
        monkeypatch,
        [
            _comprobacion(_resultado("github", "github.com", exists=True)),
            _comprobacion(_resultado("adobe", "adobe.com", rateLimit=True)),
            _comprobacion(_resultado("nike", "nike.com", rateLimit=True)),
        ],
    )

    result = await HoleheModule().run("alguien@example.com", recorder)

    assert result["limitados"] == ["adobe", "nike"]
    assert "2 servicios no respondieron" in recorder.text


@pytest.mark.asyncio
async def test_sin_hallazgos(monkeypatch, recorder) -> None:
    _patch_enrichment(monkeypatch)
    _patch_websites(
        monkeypatch, [_comprobacion(_resultado("github", "github.com", exists=False))]
    )

    result = await HoleheModule().run("alguien@example.com", recorder)

    assert result["sitios_detectados"] == []
    assert "No se detectaron registros activos" in recorder.text


# ---------------------------------------------------------------- robustez


@pytest.mark.asyncio
async def test_una_comprobacion_que_falla_no_aborta_el_resto(
    monkeypatch, recorder
) -> None:
    """Los módulos de Holehe parsean HTML ajeno y pueden lanzar cualquier cosa."""

    async def explota(email, client, out):
        raise IndexError("respuesta con un formato inesperado")

    explota.__name__ = "roto"

    async def timeout(email, client, out):
        raise httpx.ConnectTimeout("agotado")

    timeout.__name__ = "lento"

    _patch_enrichment(monkeypatch)
    _patch_websites(
        monkeypatch,
        [
            explota,
            timeout,
            _comprobacion(_resultado("github", "github.com", exists=True)),
        ],
    )

    result = await HoleheModule().run("alguien@example.com", recorder)

    assert result["status"] == "success"
    assert result["sitios_detectados"] == ["github.com"]


@pytest.mark.asyncio
async def test_la_cancelacion_se_propaga(monkeypatch, recorder) -> None:
    """CancelledError hereda de BaseException: no debe quedar atrapada."""

    async def lento(email, client, out):
        await asyncio.sleep(30)

    lento.__name__ = "lento"

    _patch_enrichment(monkeypatch)
    _patch_websites(monkeypatch, [lento])

    task = asyncio.create_task(HoleheModule().run("alguien@example.com", recorder))
    await asyncio.sleep(0.1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_progreso_por_lotes(monkeypatch, recorder) -> None:
    """Con muchos sitios se informa del avance para que la GUI no parezca colgada."""
    _patch_enrichment(monkeypatch)
    _patch_websites(
        monkeypatch,
        [_comprobacion(_resultado(f"sitio{i}", f"sitio{i}.com")) for i in range(60)],
    )

    await HoleheModule().run("alguien@example.com", recorder)

    assert "Consultando 60 servicios" in recorder.text
    assert "25/60 comprobados" in recorder.text
    assert "50/60 comprobados" in recorder.text
