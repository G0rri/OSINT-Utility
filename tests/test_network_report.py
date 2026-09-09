"""Pruebas del informe de red.

Los tres submódulos se sustituyen por dobles, de modo que la composición del
informe se comprueba sin red y de forma determinista.
"""

import asyncio

import pytest

from core import extractors
from core.case import Entidad
from modules.network_report_module import NetworkReportModule


class Recorder:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, text: str) -> None:
        self.lines.append(text)

    @property
    def text(self) -> str:
        return "".join(self.lines)


class ModuloFalso:
    """Doble de un submódulo: devuelve un resultado fijo."""

    def __init__(
        self, resultado, retardo: float = 0.0, explota: Exception | None = None
    ):
        self.name = "falso"
        self._resultado = resultado
        self._retardo = retardo
        self._explota = explota
        self.recibido: str | None = None

    def check_health(self):
        return "ok", "informe_ok"

    async def run(self, target, callback):
        self.recibido = target
        if self._retardo:
            await asyncio.sleep(self._retardo)
        if self._explota is not None:
            raise self._explota
        return self._resultado


WHOIS_OK = {
    "status": "success",
    "whois": {
        "registrar": "MarkMonitor, Inc.",
        "creation": "2007-10-09 18:20:50+00:00",
        "expiration": "2028-10-09 18:20:50+00:00",
        "name_servers": ["dns1.p08.nsone.net", "dns2.p08.nsone.net"],
    },
    "dns": {"A": ["140.82.121.3"], "MX": ["10 mail.test."]},
}

PUERTOS_OK = {
    "status": "success",
    "target": "github.com",
    "ip": "140.82.121.3",
    "ports": [22, 80, 443],
}

CABECERAS_OK = {
    "status": "success",
    "target": "github.com",
    "server": "github.com",
    "headers": {
        "hsts": "max-age=31536000",
        "csp": "default-src 'self'",
        "x_frame": "deny",
        "x_content_type": "nosniff",
    },
}


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


def _montar(modulo, whois=WHOIS_OK, puertos=PUERTOS_OK, cabeceras=CABECERAS_OK):
    modulo._whois = whois if hasattr(whois, "run") else ModuloFalso(whois)
    modulo._puertos = puertos if hasattr(puertos, "run") else ModuloFalso(puertos)
    modulo._cabeceras = (
        cabeceras if hasattr(cabeceras, "run") else ModuloFalso(cabeceras)
    )
    return modulo


# ------------------------------------------------------------- composición


@pytest.mark.asyncio
async def test_el_informe_tiene_las_tres_secciones(recorder) -> None:
    resultado = await _montar(NetworkReportModule()).run("github.com", recorder)

    assert resultado["status"] == "success"
    for seccion in ("Registro", "Infraestructura", "Seguridad web"):
        assert seccion in recorder.text, f"falta la sección {seccion}"


@pytest.mark.asyncio
async def test_muestra_los_datos_clave(recorder) -> None:
    await _montar(NetworkReportModule()).run("github.com", recorder)
    texto = recorder.text

    assert "MarkMonitor, Inc." in texto
    assert "140.82.121.3" in texto
    assert "22, 80, 443" in texto
    assert "dns1.p08.nsone.net" in texto
    assert "(+1)" in texto  # el resto de servidores se resume


@pytest.mark.asyncio
async def test_recorta_la_hora_de_las_fechas(recorder) -> None:
    """La hora de alta de un dominio es ruido en un informe."""
    await _montar(NetworkReportModule()).run("github.com", recorder)
    assert "2007-10-09" in recorder.text
    assert "18:20:50" not in recorder.text


@pytest.mark.asyncio
async def test_concuerda_el_plural_de_los_registros_mx(recorder) -> None:
    await _montar(NetworkReportModule()).run("github.com", recorder)
    assert "1 registro\n" in recorder.text or "1 registro " in recorder.text
    assert "1 registros" not in recorder.text


@pytest.mark.asyncio
async def test_señala_las_protecciones_ausentes(recorder) -> None:
    sin_csp = {
        **CABECERAS_OK,
        "headers": {**CABECERAS_OK["headers"], "csp": None, "x_frame": None},
    }
    await _montar(NetworkReportModule(), cabeceras=sin_csp).run("x.test", recorder)

    assert "✘ ausente" in recorder.text
    assert "Le faltan 2 protecciones" in recorder.text
    assert "CSP" in recorder.text and "X-Frame" in recorder.text


@pytest.mark.asyncio
async def test_confirma_cuando_no_falta_ninguna(recorder) -> None:
    await _montar(NetworkReportModule()).run("github.com", recorder)
    assert "Todas las protecciones comprobadas están puestas" in recorder.text


# -------------------------------------------------------------- robustez


@pytest.mark.asyncio
async def test_una_consulta_caida_no_tumba_el_informe(recorder) -> None:
    """Es la razón de ser del aislamiento por sección."""
    roto = ModuloFalso(None, explota=OSError("servidor WHOIS inaccesible"))
    resultado = await _montar(NetworkReportModule(), whois=roto).run("x.test", recorder)

    assert resultado["status"] == "success"
    assert "Sin datos" in recorder.text
    # Las otras dos secciones siguen apareciendo con sus datos.
    assert "140.82.121.3" in recorder.text
    assert "Todas las protecciones" in recorder.text
    assert "2 de 3 consultas correctas" in recorder.text


@pytest.mark.asyncio
async def test_las_tres_consultas_van_en_paralelo(recorder) -> None:
    """En serie tardaría 0,9 s; en paralelo, algo más de 0,3 s."""
    modulo = _montar(
        NetworkReportModule(),
        whois=ModuloFalso(WHOIS_OK, retardo=0.3),
        puertos=ModuloFalso(PUERTOS_OK, retardo=0.3),
        cabeceras=ModuloFalso(CABECERAS_OK, retardo=0.3),
    )

    inicio = asyncio.get_running_loop().time()
    await modulo.run("github.com", recorder)
    transcurrido = asyncio.get_running_loop().time() - inicio

    assert transcurrido < 0.6, f"parece secuencial: tardó {transcurrido:.2f}s"


@pytest.mark.asyncio
async def test_todas_reciben_el_mismo_objetivo(recorder) -> None:
    modulo = _montar(NetworkReportModule())
    await modulo.run("  github.com  ", recorder)

    for sub in (modulo._whois, modulo._puertos, modulo._cabeceras):
        assert sub.recibido == "github.com", "el objetivo llegó sin normalizar"


@pytest.mark.asyncio
async def test_la_cancelacion_se_propaga(recorder) -> None:
    modulo = _montar(NetworkReportModule(), whois=ModuloFalso(WHOIS_OK, retardo=30))
    task = asyncio.create_task(modulo.run("github.com", recorder))
    await asyncio.sleep(0.1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


# ------------------------------------------------------------- extracción


def test_el_extractor_combina_los_de_sus_componentes() -> None:
    salida = extractors.informe_red(
        {"status": "success", "whois": WHOIS_OK, "puertos": PUERTOS_OK}
    )
    tipos = {(t, v) for t, v, _ in salida}

    assert (Entidad.IP, "140.82.121.3") in tipos
    assert (Entidad.DOMINIO, "dns1.p08.nsone.net") in tipos
    assert (Entidad.PUERTO, "github.com:443") in tipos


def test_el_extractor_tolera_secciones_caidas() -> None:
    salida = extractors.informe_red(
        {"status": "success", "whois": {"status": "error"}, "puertos": PUERTOS_OK}
    )
    assert (Entidad.IP, "140.82.121.3") in {(t, v) for t, v, _ in salida}
