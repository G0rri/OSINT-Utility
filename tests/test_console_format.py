"""Pruebas de la lógica de formato de la consola, sin depender de Tk.

Se ejercitan las funciones puras que deciden el color de cada línea y localizan
las URLs; la parte de widget se cubre en la verificación sobre la GUI real.
"""

import pytest

from ui.console import _URL_PATTERN, ConsoleView


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("[*] Iniciando análisis\n", "info"),
        ("[+] Encontrado\n", "success"),
        ("[-] Sin resultados\n", "error"),
        ("[!] Tarea cancelada\n", "error"),
        ("--- [ SECCION ] ---\n", "header"),
        ("texto sin prefijo\n", None),
        ("", None),
    ],
)
def test_color_segun_prefijo(texto: str, esperado: str | None) -> None:
    assert ConsoleView._tag_for(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "urls"),
    [
        ("visita https://example.com ahora", ["https://example.com"]),
        ("http://a.test y https://b.test", ["http://a.test", "https://b.test"]),
        ("sin enlaces aquí", []),
        # El paréntesis de cierre no debe absorberse en la URL.
        ("ver (https://example.com/x) fin", ["https://example.com/x"]),
        ("ftp://no.soportado", []),
    ],
)
def test_deteccion_de_urls(texto: str, urls: list[str]) -> None:
    assert [m.group() for m in _URL_PATTERN.finditer(texto)] == urls


def test_la_url_no_incluye_espacios() -> None:
    match = _URL_PATTERN.search("https://example.com/ruta con espacios")
    assert match is not None
    assert match.group() == "https://example.com/ruta"
