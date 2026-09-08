"""Memoria de la investigación: qué se ha descubierto y de dónde salió.

Hasta ahora cada módulo escribía su resultado en la consola y el diccionario que
devolvía se descartaba, de modo que encadenar dos herramientas obligaba a copiar
y pegar a mano. `Caso` conserva esos resultados como hallazgos tipados, evita
duplicados y recuerda la procedencia de cada dato.

El tipo de un hallazgo es lo que permite encadenar: si algo es un DOMINIO, el
catálogo de `core.registry` ya sabe qué herramientas aceptan dominios.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Entidad(str, Enum):
    """Tipos de dato que la aplicación sabe distinguir.

    Los primeros son *pivotables*: hay herramientas que los aceptan como
    objetivo. Los últimos son hallazgos terminales, valiosos como información
    pero que no alimentan a ningún módulo.
    """

    EMAIL = "email"
    DOMINIO = "dominio"
    IP = "ip"
    USERNAME = "username"
    TELEFONO = "telefono"
    URL = "url"
    FICHERO = "fichero"

    # Terminales
    SERVICIO = "servicio"
    BRECHA = "brecha"
    PUERTO = "puerto"
    COORDENADA = "coordenada"

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS.get(self, self.value)


_ETIQUETAS: dict[Entidad, str] = {
    Entidad.EMAIL: "Correo",
    Entidad.DOMINIO: "Dominio",
    Entidad.IP: "IP",
    Entidad.USERNAME: "Usuario",
    Entidad.TELEFONO: "Teléfono",
    Entidad.URL: "URL",
    Entidad.FICHERO: "Fichero",
    Entidad.SERVICIO: "Servicio",
    Entidad.BRECHA: "Brecha",
    Entidad.PUERTO: "Puerto",
    Entidad.COORDENADA: "Coordenada",
}


@dataclass(frozen=True)
class Hallazgo:
    """Un dato descubierto, con la traza de cómo se llegó a él.

    `origen` y `desde` son la procedencia: qué herramienta lo produjo y sobre
    qué objetivo se ejecutaba. Sin eso, un caso con varios saltos encadenados no
    se puede auditar.
    """

    tipo: Entidad
    valor: str
    origen: str = ""
    desde: str = ""
    detalle: str = ""
    momento: datetime = field(default_factory=datetime.now, compare=False)

    @property
    def clave(self) -> tuple[Entidad, str]:
        return (self.tipo, self.valor)

    def __str__(self) -> str:
        base: str = f"{self.tipo.etiqueta}: {self.valor}"
        return f"{base} ({self.detalle})" if self.detalle else base


class Caso:
    """Conjunto de hallazgos acumulados durante una sesión de investigación."""

    def __init__(self) -> None:
        self._hallazgos: dict[tuple[Entidad, str], Hallazgo] = {}

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def añadir(self, hallazgo: Hallazgo) -> bool:
        """Incorpora un hallazgo. Devuelve False si ya se conocía.

        La primera aparición es la que se conserva: interesa saber cómo se
        descubrió algo, no la última vez que se volvió a ver.
        """
        if not hallazgo.valor.strip():
            return False
        if hallazgo.clave in self._hallazgos:
            return False
        self._hallazgos[hallazgo.clave] = hallazgo
        return True

    def incorporar(self, hallazgos: list[Hallazgo]) -> list[Hallazgo]:
        """Añade varios hallazgos y devuelve solo los que eran nuevos."""
        return [h for h in hallazgos if self.añadir(h)]

    def limpiar(self) -> None:
        self._hallazgos.clear()

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def todos(self) -> list[Hallazgo]:
        return list(self._hallazgos.values())

    def de_tipo(self, tipo: Entidad) -> list[Hallazgo]:
        return [h for h in self._hallazgos.values() if h.tipo == tipo]

    def tipo_de(self, valor: str) -> Entidad | None:
        """Tipo asociado a un valor concreto, si se conoce."""
        for (tipo, val), _ in self._hallazgos.items():
            if val == valor:
                return tipo
        return None

    def indice_por_valor(self) -> dict[str, Entidad]:
        """Mapa valor -> tipo, para localizar los hallazgos dentro de un texto.

        Cuando un mismo valor aparece con dos tipos gana el pivotable, que es el
        que ofrece acciones al usuario.
        """
        indice: dict[str, Entidad] = {}
        for tipo, valor in self._hallazgos:
            actual: Entidad | None = indice.get(valor)
            if actual is None or (not es_pivotable(actual) and es_pivotable(tipo)):
                indice[valor] = tipo
        return indice

    def resumen(self) -> dict[Entidad, int]:
        """Recuento de hallazgos por tipo, en orden de declaración."""
        conteo: dict[Entidad, int] = {}
        for tipo, _ in self._hallazgos:
            conteo[tipo] = conteo.get(tipo, 0) + 1
        return {t: conteo[t] for t in Entidad if t in conteo}

    def __len__(self) -> int:
        return len(self._hallazgos)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, Hallazgo):
            return item.clave in self._hallazgos
        return any(valor == item for _, valor in self._hallazgos)


# Tipos que alguna herramienta acepta como objetivo. Se define aquí, y no en el
# registro, para que `Caso` no dependa de la interfaz ni de los módulos.
_PIVOTABLES: frozenset[Entidad] = frozenset(
    {
        Entidad.EMAIL,
        Entidad.DOMINIO,
        Entidad.IP,
        Entidad.USERNAME,
        Entidad.TELEFONO,
        Entidad.URL,
        Entidad.FICHERO,
    }
)


def es_pivotable(tipo: Entidad) -> bool:
    """Indica si el tipo puede usarse como objetivo de otra herramienta."""
    return tipo in _PIVOTABLES
