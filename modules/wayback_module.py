import logging
from typing import Any, Callable

import httpx

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)


class WaybackModule(BaseModule):
    """Módulo OSINT para recuperar y analizar registros históricos en la Wayback Machine."""

    def __init__(self) -> None:
        # Inicialización obligatoria pasando el identificador exacto del módulo
        super().__init__("Wayback")

    def check_health(self) -> tuple[str, str]:
        """Verifica la disponibilidad base del módulo pericial."""
        return "ok", "wayback_ok"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Consulta de forma asíncrona la API CDX de Archive.org blindando los errores de red."""
        callback(f"[*] Consultando Wayback Machine (CDX API) para: {target}\n")

        # Solicitamos únicamente el registro cronológico más antiguo indexado
        url: str = f"http://web.archive.org/cdx/search/cdx?url={target}&output=json&limit=1&fl=timestamp,original"
        headers: dict[str, str] = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient() as client:
            try:
                response: httpx.Response = await client.get(
                    url, headers=headers, timeout=15.0
                )
                response.raise_for_status()

                data: Any = response.json()
                # El índice 0 contiene las cabeceras de columnas; el índice 1, el primer registro
                if isinstance(data, list) and len(data) > 1:
                    timestamp: str = str(data[1][0])
                    original_url: str = str(data[1][1])

                    # Transformación del formato nativo YYYYMMDDhhmmss a ISO YYYY-MM-DD
                    formatted_date: str = (
                        f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
                    )
                    snapshot_url: str = (
                        f"https://web.archive.org/web/{timestamp}/{original_url}"
                    )

                    callback("[+] ¡Captura histórica encontrada!\n")
                    callback(
                        f"    - Fecha del registro más antiguo: {formatted_date}\n"
                    )
                    callback(f"    - Enlace al archivo: {snapshot_url}\n")
                else:
                    callback(
                        "[-] No se encontraron capturas históricas para este objetivo.\n"
                    )

            except httpx.HTTPStatusError as err:
                logger.error(
                    "Error de estado HTTP %d devuelto por Archive.org: %s",
                    err.response.status_code,
                    err,
                )
                callback(
                    f"[-] Error devuelto por Archive.org: Código HTTP {err.response.status_code}\n"
                )
                return {"status": "error", "error": f"HTTP {err.response.status_code}"}

            except httpx.TimeoutException as err:
                logger.warning(
                    "Tiempo de espera agotado al conectar con Wayback Machine: %s", err
                )
                callback(
                    "[-] Error de red: Tiempo de espera agotado con los servidores de Archive.org.\n"
                )
                return {"status": "error", "error": "timeout"}

            except httpx.RequestError as err:
                logger.error(
                    "Fallo de comunicación/transporte de red con Archive.org: %s", err
                )
                callback(
                    f"[-] Error de red crítico al conectar con la Wayback Machine: {err}\n"
                )
                return {"status": "error", "error": str(err)}

        callback("\n[+] Consulta finalizada.\n")
        return {"status": "success", "target": target}
