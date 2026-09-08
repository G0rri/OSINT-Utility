"""Catálogo declarativo de las herramientas OSINT disponibles.

Antes, dar de alta un módulo obligaba a tocar cuatro puntos distintos de
`main.py`: instanciarlo, mapearlo por nombre, crear su radio button y añadir su
placeholder. Aquí toda esa información vive en una sola entrada de `TOOLS`, y
tanto la interfaz como el despachador de tareas se construyen a partir de ella.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from core import extractors
from core.base_module import BaseModule
from core.case import Entidad
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


@dataclass(frozen=True)
class Category:
    """Una pestaña de la interfaz."""

    key: str
    label_key: str
    padx: int = 10


@dataclass(frozen=True)
class ToolOption:
    """Casilla de configuración que acompaña a una herramienta concreta.

    `setter` es el nombre del método del módulo que recibe el valor booleano
    (por ejemplo `toggle_google_search`). Se resuelve por nombre para que el
    catálogo no dependa de instancias concretas.
    """

    label_key: str
    setter: str
    tooltip_key: str | None = None
    default: bool = False


@dataclass(frozen=True)
class ToolSpec:
    """Descripción completa de una herramienta: metadatos, fábrica y opciones."""

    key: str
    category: str
    label_key: str
    placeholder_key: str
    factory: Callable[[], BaseModule]
    option: ToolOption | None = None
    needs_file: bool = False

    # Tipos de entidad que la herramienta acepta como objetivo. Es lo que
    # permite ofrecer acciones sobre un hallazgo sin cablear cada cadena a mano.
    consume: tuple[Entidad, ...] = ()
    # Tipos que la herramienta puede descubrir, y función que los extrae de su
    # diccionario de resultado.
    produce: tuple[Entidad, ...] = ()
    extractor: extractors.Extractor = extractors.sin_hallazgos


CATEGORIES: tuple[Category, ...] = (
    Category(key="identities", label_key="tab_identities", padx=20),
    Category(key="network", label_key="tab_network", padx=10),
    Category(key="forensics", label_key="tab_forensics", padx=20),
)

# El orden dentro de cada categoría es el de aparición en la pestaña, y la
# primera herramienta de cada una es la seleccionada por defecto.
TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        key="Holehe",
        category="identities",
        label_key="holehe_desc",
        placeholder_key="placeholder_holehe",
        factory=HoleheModule,
        consume=(Entidad.EMAIL,),
        produce=(Entidad.SERVICIO, Entidad.BRECHA, Entidad.URL),
        extractor=extractors.holehe,
    ),
    ToolSpec(
        key="Sherlock",
        category="identities",
        label_key="sherlock_desc",
        placeholder_key="placeholder_sherlock",
        factory=SherlockModule,
        consume=(Entidad.USERNAME,),
        produce=(Entidad.URL,),
        extractor=extractors.sherlock,
    ),
    ToolSpec(
        key="PhoneInfoga",
        category="identities",
        label_key="phoneinfoga_desc",
        placeholder_key="placeholder_phoneinfoga",
        factory=PhoneInfogaModule,
        option=ToolOption(
            label_key="chk_google_search",
            setter="toggle_google_search",
            tooltip_key="chk_google_search_tip",
        ),
        consume=(Entidad.TELEFONO,),
    ),
    ToolSpec(
        key="VirusTotal",
        category="network",
        label_key="virustotal_desc",
        placeholder_key="placeholder_virustotal",
        factory=VirustotalModule,
        consume=(Entidad.DOMINIO, Entidad.IP),
    ),
    ToolSpec(
        key="WHOIS",
        category="network",
        label_key="whois_desc",
        placeholder_key="placeholder_whois",
        factory=WhoisDnsModule,
        consume=(Entidad.DOMINIO,),
        produce=(Entidad.IP, Entidad.DOMINIO),
        extractor=extractors.whois_dns,
    ),
    ToolSpec(
        key="Subdominios",
        category="network",
        label_key="subdomains_desc",
        placeholder_key="placeholder_subdomains",
        factory=SubdomainModule,
        consume=(Entidad.DOMINIO,),
        produce=(Entidad.DOMINIO,),
        extractor=extractors.subdominios,
    ),
    ToolSpec(
        key="PortScanner",
        category="network",
        label_key="ports_desc",
        placeholder_key="placeholder_ports",
        factory=PortScannerModule,
        consume=(Entidad.DOMINIO, Entidad.IP),
        produce=(Entidad.IP, Entidad.PUERTO),
        extractor=extractors.escaner_puertos,
    ),
    ToolSpec(
        key="SecurityHeaders",
        category="network",
        label_key="headers_desc",
        placeholder_key="placeholder_headers",
        factory=SecurityHeadersModule,
        option=ToolOption(
            label_key="chk_insecure_ssl",
            setter="toggle_insecure_ssl",
            tooltip_key="chk_insecure_ssl_tip",
        ),
        consume=(Entidad.DOMINIO, Entidad.URL),
    ),
    ToolSpec(
        key="Metadatos",
        category="forensics",
        label_key="metadata_desc",
        placeholder_key="placeholder_metadata",
        factory=MetadataModule,
        needs_file=True,
        consume=(Entidad.FICHERO,),
        produce=(Entidad.COORDENADA,),
        extractor=extractors.metadatos,
    ),
    ToolSpec(
        key="Wayback",
        category="forensics",
        label_key="wayback_desc",
        placeholder_key="placeholder_wayback",
        factory=WaybackModule,
        consume=(Entidad.DOMINIO, Entidad.URL),
        produce=(Entidad.URL,),
        extractor=extractors.wayback,
    ),
)


@dataclass
class ToolRegistry:
    """Instancia una única vez cada módulo y los expone por clave.

    Las instancias se crean al construir el registro (no al importar), de modo
    que el `.env` ya está cargado cuando los módulos leen su configuración.
    """

    _modules: dict[str, BaseModule] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._modules = {spec.key: spec.factory() for spec in TOOLS}

    def module(self, key: str) -> BaseModule | None:
        """Devuelve la instancia asociada a una clave de herramienta."""
        return self._modules.get(key)

    def spec(self, key: str) -> ToolSpec | None:
        """Devuelve los metadatos de una herramienta."""
        return next((spec for spec in TOOLS if spec.key == key), None)

    def specs_for(self, category: str) -> list[ToolSpec]:
        """Herramientas de una categoría, en orden de aparición."""
        return [spec for spec in TOOLS if spec.category == category]

    def herramientas_para(self, tipo: Entidad) -> list[ToolSpec]:
        """Herramientas que aceptan ese tipo de entidad como objetivo.

        Es lo que convierte un hallazgo en accionable: dado un DOMINIO nuevo, el
        catálogo ya sabe que WHOIS, Subdominios, Puertos, VirusTotal, Cabeceras
        y Wayback pueden trabajar sobre él, sin cablear ninguna cadena a mano.
        """
        return [spec for spec in TOOLS if tipo in spec.consume]

    def default_for(self, category: str) -> str:
        """Clave de la herramienta seleccionada por defecto en una categoría."""
        specs = self.specs_for(category)
        return specs[0].key if specs else ""

    def __iter__(self):
        return iter(TOOLS)
