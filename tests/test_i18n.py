"""Verifica la integridad del sistema de traducciones.

Es la prueba que habría detectado las claves de tooltip ausentes (`ports_ok`,
`wayback_ok`, `whois_ok`, `subdomains_ok`, `headers_ok`), que se mostraban
crudas en la interfaz porque `Translator.get` devuelve la clave si no la halla.
"""

import json
import os

import pytest

from core.i18n import Translator
from modules.holehe_module import HoleheModule
from modules.metadata_module import MetadataModule
from modules.phoneinfoga_module import PhoneInfogaModule
from modules.port_scanner_module import PortScannerModule
from modules.security_headers_module import SecurityHeadersModule
from modules.sherlock_module import SherlockModule
from modules.subdomain_module import SubdomainModule
from modules.virustotal_module import VirustotalModule
from modules.wayback_module import WaybackModule
from modules.whois_dns_module import WhoisDnsModule

LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locales"
)
LANGS = ("es", "en")

ALL_MODULES = [
    HoleheModule,
    SherlockModule,
    PhoneInfogaModule,
    VirustotalModule,
    WhoisDnsModule,
    SubdomainModule,
    PortScannerModule,
    SecurityHeadersModule,
    WaybackModule,
    MetadataModule,
]


def _load(lang: str) -> dict[str, str]:
    with open(os.path.join(LOCALES_DIR, f"{lang}.json"), encoding="utf-8") as f:
        return json.load(f)


def test_locales_tienen_las_mismas_claves() -> None:
    es, en = _load("es"), _load("en")
    assert set(es) == set(en), (
        f"Solo en es.json: {sorted(set(es) - set(en))} | "
        f"Solo en en.json: {sorted(set(en) - set(es))}"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_ninguna_traduccion_esta_vacia(lang: str) -> None:
    for key, value in _load(lang).items():
        assert value.strip(), f"La clave '{key}' está vacía en {lang}.json"


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("module_cls", ALL_MODULES, ids=lambda c: c.__name__)
def test_check_health_devuelve_una_clave_traducible(module_cls, lang: str) -> None:
    """El segundo elemento de check_health debe ser una clave de los locales.

    Devolver texto fijo (como hacían Holehe y PhoneInfoga) rompe el cambio de
    idioma; devolver una clave inexistente muestra el identificador en el tooltip.
    """
    catalog = _load(lang)
    status, msg_key = module_cls().check_health()

    assert status in {"ok", "warning", "error", "none"}, (
        f"{module_cls.__name__} devolvió un estado desconocido: {status!r}"
    )

    if not msg_key:
        return

    assert msg_key in catalog, (
        f"{module_cls.__name__} devuelve '{msg_key}', que no existe en {lang}.json"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_translator_carga_y_traduce(lang: str) -> None:
    translator = Translator(lang.upper())
    assert translator.lang == lang.upper()
    assert translator.get("search_btn") != "search_btn"


def test_translator_devuelve_la_clave_si_no_existe() -> None:
    """Comportamiento documentado del fallback: hace visible cualquier clave ausente."""
    assert Translator("ES").get("clave_que_no_existe") == "clave_que_no_existe"
