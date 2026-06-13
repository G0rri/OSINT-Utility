import asyncio
import logging
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from core.base_module import BaseModule
from core.visualizer import NetworkVisualizer

logger: logging.Logger = logging.getLogger(__name__)


class SubdomainModule(BaseModule):
    """Módulo OSINT para el descubrimiento y visualización interactiva de subdominios."""

    def __init__(self) -> None:
        super().__init__("Subdomain Scanner")
        self.description: str = (
            "Búsqueda asíncrona de subdominios usando crt.sh y HackerTarget"
        )

    def check_health(self) -> tuple[str, str]:
        """Verifica el estado de salud y disponibilidad operacional del módulo."""
        return "ok", "subdomains_ok"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Ejecuta las consultas asíncronas a las APIs externas y renderiza el grafo de relaciones."""
        callback(f"[*] Iniciando búsqueda de subdominios para: {target}\n")

        target = target.strip().lower()
        if "://" in target:
            target = urlparse(target).netloc or target
        else:
            target = urlparse(f"http://{target}").netloc or target

        target = target.split(":")[0]
        subdomains: set[str] = set()

        async with httpx.AsyncClient(timeout=25.0) as client:
            # --- Fuente 1: crt.sh ---
            callback("[*] Consultando crt.sh...\n")
            crtsh_url: str = f"https://crt.sh/?q=%.{target}&output=json"
            try:
                response: httpx.Response = await client.get(crtsh_url)
                response.raise_for_status()
                data: Any = response.json()

                if isinstance(data, list):
                    for entry in data:
                        name_value: str = entry.get("name_value", "")
                        for sub in name_value.splitlines():
                            sub = sub.strip().lower()
                            if sub.startswith("*."):
                                sub = sub[2:]
                            if (
                                sub
                                and "@" not in sub
                                and (sub.endswith(f".{target}") or sub == target)
                            ):
                                if sub != target:
                                    subdomains.add(sub)
                    callback(
                        f"[+] crt.sh: {len(subdomains)} subdominios encontrados.\n"
                    )
                else:
                    callback("[-] crt.sh: Respuesta inesperada de la plataforma.\n")

            except httpx.HTTPStatusError as err:
                logger.error(
                    "Error HTTP %d devuelto por crt.sh: %s",
                    err.response.status_code,
                    err,
                )
                callback(
                    f"[-] crt.sh: Error HTTP {err.response.status_code}. Continuando con siguiente fuente...\n"
                )
            except httpx.TimeoutException as err:
                logger.warning(
                    "Tiempo de espera agotado al conectar con crt.sh: %s", err
                )
                callback("[-] crt.sh: Tiempo de espera agotado. Continuando...\n")
            except httpx.RequestError as err:
                logger.error("Fallo de red al conectar con crt.sh: %s", err)
                callback("[-] crt.sh: Error de conexión general. Continuando...\n")

            # --- Fuente 2: HackerTarget ---
            callback("[*] Consultando HackerTarget...\n")
            ht_url: str = f"https://api.hackertarget.com/hostsearch/?q={target}"
            try:
                response = await client.get(ht_url, timeout=20.0)
                response.raise_for_status()

                if "error" not in response.text.lower()[:50]:
                    count_before: int = len(subdomains)
                    for line in response.text.splitlines():
                        parts: list[str] = line.split(",")
                        if parts:
                            sub = parts[0].strip().lower()
                            if sub and "@" not in sub and sub.endswith(f".{target}"):
                                subdomains.add(sub)
                    new_found: int = len(subdomains) - count_before
                    callback(
                        f"[+] HackerTarget: {new_found} subdominios adicionales encontrados.\n"
                    )
                else:
                    callback(
                        "[-] HackerTarget: Sin resultados o límite de API alcanzado.\n"
                    )

            except httpx.HTTPStatusError as err:
                logger.error(
                    "Error HTTP %d devuelto por HackerTarget: %s",
                    err.response.status_code,
                    err,
                )
                callback(f"[-] HackerTarget: Error HTTP {err.response.status_code}.\n")
            except httpx.TimeoutException as err:
                logger.warning(
                    "Tiempo de espera agotado al conectar con HackerTarget: %s", err
                )
                callback("[-] HackerTarget: Tiempo de espera agotado.\n")
            except httpx.RequestError as err:
                logger.error("Fallo de red al conectar con HackerTarget: %s", err)
                callback("[-] HackerTarget: Error de conexión de red.\n")

        if subdomains:
            sorted_subs: list[str] = sorted(list(subdomains))
            callback(
                f"\n[+] Total: {len(sorted_subs)} subdominios únicos encontrados:\n"
            )
            for sub in sorted_subs:
                callback(f"    - {sub}\n")
                await asyncio.sleep(0.005)

            # --- Generar Grafo ---
            callback("\n[*] Generando grafo interactivo de red...\n")
            try:
                graph_path: str = NetworkVisualizer.generate_subdomain_graph(
                    target, sorted_subs
                )
                NetworkVisualizer.open_in_browser(graph_path)
                callback("[+] Grafo abierto en el navegador predeterminado.\n")
                callback(f"    (Archivo temporal: {graph_path})\n")
            except (OSError, RuntimeError) as err:
                logger.error(
                    "Fallo al procesar o instanciar el mapa relacional del grafo: %s",
                    err,
                )
                callback(f"[-] Error al generar/abrir el grafo interactivo: {err}\n")

            callback("\n[+] Búsqueda de subdominios finalizada.\n")
            return {"status": "success", "target": target, "subdomains": sorted_subs}
        else:
            callback("[-] No se encontraron subdominios en ninguna fuente analizada.\n")
            return {"status": "success", "target": target, "subdomains": []}
