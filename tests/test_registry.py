"""Pruebas del catálogo declarativo de herramientas.

El catálogo es ahora la única fuente de verdad de la interfaz: si una entrada
apunta a una clave de traducción inexistente o a un método que el módulo no
implementa, el fallo aparece aquí y no en tiempo de ejecución.
"""

import json
import os

import pytest

from core.base_module import BaseModule
from core.registry import CATEGORIES, TOOLS, ToolRegistry

LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locales"
)
LANGS = ("es", "en")


def _catalog(lang: str) -> dict[str, str]:
    with open(os.path.join(LOCALES_DIR, f"{lang}.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def registry() -> ToolRegistry:
    return ToolRegistry()


def test_las_claves_de_herramienta_son_unicas() -> None:
    keys = [spec.key for spec in TOOLS]
    assert len(keys) == len(set(keys)), f"Claves duplicadas: {keys}"


def test_toda_herramienta_pertenece_a_una_categoria_declarada() -> None:
    categorias = {c.key for c in CATEGORIES}
    for spec in TOOLS:
        assert spec.category in categorias, (
            f"{spec.key} apunta a la categoría inexistente '{spec.category}'"
        )


def test_toda_categoria_tiene_al_menos_una_herramienta(registry: ToolRegistry) -> None:
    for category in CATEGORIES:
        assert registry.specs_for(category.key), f"{category.key} está vacía"
        assert registry.default_for(category.key), f"{category.key} sin default"


@pytest.mark.parametrize("lang", LANGS)
def test_todas_las_claves_de_traduccion_existen(lang: str) -> None:
    """Cubre etiquetas, placeholders, pestañas y casillas de opción."""
    catalog = _catalog(lang)

    for category in CATEGORIES:
        assert category.label_key in catalog, (
            f"Categoría '{category.key}': falta '{category.label_key}' en {lang}.json"
        )

    for spec in TOOLS:
        assert spec.label_key in catalog, (
            f"{spec.key}: falta '{spec.label_key}' en {lang}.json"
        )
        assert spec.placeholder_key in catalog, (
            f"{spec.key}: falta '{spec.placeholder_key}' en {lang}.json"
        )
        # El tooltip de ayuda deriva cuatro claves del mismo prefijo.
        for sufijo in ("_desc", "_body", "_needs", "_gives"):
            clave = f"{spec.help_key}{sufijo}"
            assert clave in catalog, f"{spec.key}: falta '{clave}' en {lang}.json"
        if spec.option is not None:
            assert spec.option.label_key in catalog, (
                f"{spec.key}: falta '{spec.option.label_key}' en {lang}.json"
            )
            if spec.option.tooltip_key:
                assert spec.option.tooltip_key in catalog, (
                    f"{spec.key}: falta '{spec.option.tooltip_key}' en {lang}.json"
                )


def test_las_fabricas_producen_modulos_validos(registry: ToolRegistry) -> None:
    for spec in TOOLS:
        module = registry.module(spec.key)
        assert isinstance(module, BaseModule), f"{spec.key} no hereda de BaseModule"


def test_el_registro_reutiliza_la_misma_instancia(registry: ToolRegistry) -> None:
    """La interfaz consulta check_health y ejecuta run sobre el mismo objeto."""
    for spec in TOOLS:
        assert registry.module(spec.key) is registry.module(spec.key)


def test_las_opciones_apuntan_a_metodos_existentes(registry: ToolRegistry) -> None:
    """El setter se resuelve por nombre; un typo debe detectarse aquí."""
    for spec in TOOLS:
        if spec.option is None:
            continue
        module = registry.module(spec.key)
        setter = getattr(module, spec.option.setter, None)
        assert callable(setter), (
            f"{spec.key}: '{spec.option.setter}' no existe o no es invocable"
        )
        setter(True)
        setter(False)


@pytest.mark.parametrize("lang", LANGS)
def test_los_titulares_de_ayuda_dicen_que_obtienes(lang: str) -> None:
    """El titular describe el resultado, no el nombre de la herramienta.

    Repetir la etiqueta del radio en el tooltip no aporta nada; el titular tiene
    que responder a "¿para qué me sirve esto?".
    """
    catalog = _catalog(lang)
    for spec in TOOLS:
        titular = catalog[f"{spec.help_key}_desc"]
        etiqueta = catalog[spec.label_key]
        assert titular.lower() != etiqueta.lower(), (
            f"{spec.key}: el titular repite la etiqueta '{etiqueta}'"
        )
        assert len(titular.split()) >= 3, (
            f"{spec.key}: el titular '{titular}' es demasiado escueto"
        )


@pytest.mark.parametrize("lang", LANGS)
def test_toda_ayuda_indica_que_escribir_y_que_esperar(lang: str) -> None:
    catalog = _catalog(lang)
    for spec in TOOLS:
        for sufijo in ("_body", "_needs", "_gives"):
            texto = catalog[f"{spec.help_key}{sufijo}"]
            assert texto.strip(), f"{spec.key}{sufijo} está vacío"


def test_solo_metadatos_requiere_fichero_local() -> None:
    con_fichero = [spec.key for spec in TOOLS if spec.needs_file]
    assert con_fichero == ["Metadatos"]


def test_spec_desconocida_devuelve_none(registry: ToolRegistry) -> None:
    assert registry.spec("NoExiste") is None
    assert registry.module("NoExiste") is None


def test_los_defaults_son_la_primera_herramienta(registry: ToolRegistry) -> None:
    assert registry.default_for("identities") == "Holehe"
    assert registry.default_for("network") == "VirusTotal"
    assert registry.default_for("forensics") == "Metadatos"
