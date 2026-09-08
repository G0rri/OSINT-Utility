"""Pruebas de los módulos de red con transportes httpx simulados.

No se abre ninguna conexión real: `httpx.MockTransport` intercepta las peticiones,
lo que permite ejercitar tanto las rutas de éxito como los códigos de error.
"""

import httpx
import pytest

from modules.port_scanner_module import PortScannerModule
from modules.security_headers_module import SecurityHeadersModule
from modules.virustotal_module import VirustotalModule
from modules.wayback_module import WaybackModule


class Recorder:
    """Acumula la salida que los módulos envían a la consola de la GUI."""

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


def _patch_client(monkeypatch, handler) -> None:
    """Sustituye httpx.AsyncClient por uno con transporte simulado."""
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("verify", None)
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


# --------------------------- VirusTotal ---------------------------


@pytest.mark.asyncio
async def test_virustotal_sin_api_key_no_hace_peticiones(monkeypatch, recorder) -> None:
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)
    module = VirustotalModule()
    module.api_key = None

    result = await module.run("example.com", recorder)

    assert result["status"] == "error"
    assert result["error"] == "Missing API Key"
    assert "VIRUSTOTAL_API_KEY" in recorder.text


@pytest.mark.asyncio
async def test_virustotal_parsea_estadisticas(monkeypatch, recorder) -> None:
    payload = {
        "data": {
            "attributes": {
                "last_analysis_stats": {
                    "malicious": 3,
                    "suspicious": 1,
                    "harmless": 60,
                    "undetected": 8,
                }
            }
        }
    }
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json=payload))

    module = VirustotalModule()
    module.api_key = "clave-de-prueba"
    result = await module.run("example.com", recorder)

    assert result["status"] == "success"
    assert result["stats"]["malicious"] == 3
    assert "3" in recorder.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "fragmento"),
    [(401, "401"), (404, "404"), (429, "429")],
)
async def test_virustotal_traduce_errores_http(
    monkeypatch, recorder, code: int, fragmento: str
) -> None:
    _patch_client(monkeypatch, lambda req: httpx.Response(code, json={}))

    module = VirustotalModule()
    module.api_key = "clave-de-prueba"
    result = await module.run("example.com", recorder)

    assert result["status"] == "error"
    assert result["error"] == f"HTTP {code}"
    assert fragmento in recorder.text


# --------------------------- Wayback ---------------------------


@pytest.mark.asyncio
async def test_wayback_formatea_la_fecha_mas_antigua(monkeypatch, recorder) -> None:
    payload = [
        ["timestamp", "original"],
        ["19981212093000", "http://example.com/"],
    ]
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json=payload))

    result = await WaybackModule().run("example.com", recorder)

    assert result["status"] == "success"
    assert "1998-12-12" in recorder.text
    assert "web.archive.org/web/19981212093000" in recorder.text


@pytest.mark.asyncio
async def test_wayback_sin_capturas(monkeypatch, recorder) -> None:
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json=[]))

    result = await WaybackModule().run("example.com", recorder)

    assert result["status"] == "success"
    assert "No se encontraron capturas" in recorder.text


# --------------------------- Port Scanner ---------------------------


@pytest.mark.asyncio
async def test_port_scanner_lista_puertos(monkeypatch, recorder) -> None:
    monkeypatch.setattr(
        "modules.port_scanner_module.socket.gethostbyname", lambda host: "93.184.216.34"
    )
    _patch_client(
        monkeypatch, lambda req: httpx.Response(200, json={"ports": [80, 443]})
    )

    result = await PortScannerModule().run("example.com", recorder)

    assert result["status"] == "success"
    assert "Puerto 80" in recorder.text
    assert "Puerto 443" in recorder.text


@pytest.mark.asyncio
async def test_port_scanner_dns_fallido(monkeypatch, recorder) -> None:
    import socket as _socket

    def _boom(host):
        raise _socket.gaierror("nombre no resuelto")

    monkeypatch.setattr("modules.port_scanner_module.socket.gethostbyname", _boom)

    result = await PortScannerModule().run("dominio-inexistente.invalid", recorder)

    assert result["status"] == "error"
    assert result["error"] == "DNS resolution failed"


# --------------------------- Security Headers ---------------------------


def test_security_headers_verifica_tls_por_defecto() -> None:
    """La verificación TLS no debe desactivarse salvo petición explícita."""
    module = SecurityHeadersModule()
    assert module._insecure_ssl is False

    module.toggle_insecure_ssl(True)
    assert module._insecure_ssl is True

    module.toggle_insecure_ssl(False)
    assert module._insecure_ssl is False


@pytest.mark.asyncio
async def test_security_headers_detecta_cabeceras_ausentes(
    monkeypatch, recorder
) -> None:
    _patch_client(
        monkeypatch,
        lambda req: httpx.Response(200, headers={"Server": "nginx"}),
    )

    result = await SecurityHeadersModule().run("example.com", recorder)

    assert result["status"] == "success"
    assert "Strict-Transport-Security (HSTS): Faltante" in recorder.text
    assert "Content-Security-Policy (CSP): Faltante" in recorder.text
    assert "nginx" in recorder.text


@pytest.mark.asyncio
async def test_security_headers_detecta_cabeceras_presentes(
    monkeypatch, recorder
) -> None:
    headers = {
        "Server": "cloudflare",
        "Strict-Transport-Security": "max-age=31536000",
        "Content-Security-Policy": "default-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
    }
    _patch_client(monkeypatch, lambda req: httpx.Response(200, headers=headers))

    result = await SecurityHeadersModule().run("example.com", recorder)

    assert result["status"] == "success"
    assert "(HSTS): Presente" in recorder.text
    assert "[DENY]" in recorder.text
