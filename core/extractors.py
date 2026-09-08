"""Traduce el diccionario que devuelve cada módulo a hallazgos tipados.

La extracción vive aquí y no dentro de los módulos por dos motivos: los módulos
no tienen por qué conocer el modelo del caso, y así se lee de un vistazo qué
produce cada herramienta.

Nótese que esto parsea estructuras propias del proyecto, no la salida de texto
de terceros: un cambio en una librería externa no puede romperlo en silencio.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Callable
from typing import Any

from core.case import Entidad

# (tipo, valor, detalle)
Extraccion = tuple[Entidad, str, str]
Extractor = Callable[[dict[str, Any]], list[Extraccion]]


def _es_ip(valor: str) -> bool:
    try:
        ipaddress.ip_address(valor)
    except ValueError:
        return False
    return True


def sin_hallazgos(resultado: dict[str, Any]) -> list[Extraccion]:
    """Para módulos que informan pero no descubren datos encadenables."""
    return []


def subdominios(resultado: dict[str, Any]) -> list[Extraccion]:
    """Cada subdominio es un dominio nuevo, y por tanto un objetivo pivotable."""
    return [
        (Entidad.DOMINIO, str(sub), "subdominio")
        for sub in resultado.get("subdomains", [])
        if sub
    ]


def whois_dns(resultado: dict[str, Any]) -> list[Extraccion]:
    """Los registros A dan IPs; los name servers, dominios de infraestructura."""
    hallazgos: list[Extraccion] = []

    dns: dict[str, Any] = resultado.get("dns", {}) or {}
    for registro in dns.get("A", []) or []:
        valor: str = str(registro).strip()
        if _es_ip(valor):
            hallazgos.append((Entidad.IP, valor, "registro A"))

    whois: dict[str, Any] = resultado.get("whois", {}) or {}
    for ns in whois.get("name_servers", []) or []:
        valor = str(ns).strip().lower().rstrip(".")
        if valor:
            hallazgos.append((Entidad.DOMINIO, valor, "name server"))

    return hallazgos


def escaner_puertos(resultado: dict[str, Any]) -> list[Extraccion]:
    """La IP resuelta es pivotable; los puertos son hallazgos terminales."""
    hallazgos: list[Extraccion] = []

    ip: str = str(resultado.get("ip", "")).strip()
    if _es_ip(ip):
        hallazgos.append((Entidad.IP, ip, "resuelta"))

    objetivo: str = str(resultado.get("target", "")).strip()
    for puerto in resultado.get("ports", []) or []:
        etiqueta: str = f"{objetivo}:{puerto}" if objetivo else str(puerto)
        hallazgos.append((Entidad.PUERTO, etiqueta, "abierto"))

    return hallazgos


def wayback(resultado: dict[str, Any]) -> list[Extraccion]:
    snapshot: dict[str, Any] = resultado.get("snapshot", {}) or {}
    url: str = str(snapshot.get("url", "")).strip()
    if not url:
        return []
    fecha: str = str(snapshot.get("fecha", ""))
    return [(Entidad.URL, url, f"captura {fecha}" if fecha else "captura")]


def sherlock(resultado: dict[str, Any]) -> list[Extraccion]:
    return [
        (Entidad.URL, str(url), "perfil")
        for url in resultado.get("profiles", []) or []
        if url
    ]


def holehe(resultado: dict[str, Any]) -> list[Extraccion]:
    """Servicios y brechas: información valiosa, pero no objetivos pivotables."""
    hallazgos: list[Extraccion] = []

    for sitio in resultado.get("sitios_detectados", []) or []:
        hallazgos.append((Entidad.SERVICIO, str(sitio), "cuenta registrada"))

    brechas: Any = resultado.get("brechas_seguridad") or []
    if isinstance(brechas, list):
        for brecha in brechas:
            hallazgos.append((Entidad.BRECHA, str(brecha), "filtración"))

    google: dict[str, Any] = resultado.get("identidad_google", {}) or {}
    if google.get("avatar_url"):
        hallazgos.append((Entidad.URL, str(google["avatar_url"]), "avatar de Google"))

    return hallazgos


def metadatos(resultado: dict[str, Any]) -> list[Extraccion]:
    """De un fichero local interesa sobre todo la geolocalización incrustada."""
    metadata: dict[str, Any] = resultado.get("metadata", {}) or {}
    gps: Any = metadata.get("GPSInfo")
    if not isinstance(gps, dict) or not gps:
        return []

    partes: list[str] = [
        f"{clave} {valor}"
        for clave, valor in gps.items()
        if str(clave).startswith(("GPSLatitude", "GPSLongitude"))
    ]
    if not partes:
        return []
    return [(Entidad.COORDENADA, " / ".join(partes), "EXIF del fichero")]
