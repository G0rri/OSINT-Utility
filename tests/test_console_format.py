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


# ------------------------------------------------- avisos del caso


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("[#] 9 hallazgos nuevos en el caso\n", "caso"),
        ("[>] Pivotando sobre 1.2.3.4\n", "caso"),
    ],
)
def test_los_avisos_del_caso_tienen_color_propio(texto: str, esperado: str) -> None:
    """No deben confundirse con la salida de un módulo."""
    assert ConsoleView._tag_for(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "pos", "largo", "esperado"),
    [
        # example.com dentro de mail.example.com no debe marcarse.
        ("mail.example.com", 5, 11, False),
        ("ver example.com aqui", 4, 11, True),
        ("example.com", 0, 11, True),
        ("(example.com)", 1, 11, True),
        ("https://example.com/x", 8, 11, False),
        ("sub.example.com.br", 4, 11, False),
    ],
)
def test_limites_de_palabra_al_marcar(
    texto: str, pos: int, largo: int, esperado: bool
) -> None:
    assert ConsoleView._es_limite(texto, pos, largo) is esperado
