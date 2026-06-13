import logging
import os
import re
from typing import Any, Callable

import httpx

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)


class VirustotalModule(BaseModule):
    """Módulo nativo asíncrono para consultar la API v3 de VirusTotal de forma segura."""

    def __init__(self) -> None:
        super().__init__("VirusTotal")
        self.api_key: str | None = os.getenv("VIRUSTOTAL_API_KEY")

    def check_health(self) -> tuple[str, str]:
        """Comprueba si la API Key es válida y se encuentra cargada."""
        is_valid: bool = bool(
            self.api_key and self.api_key.lower() != "tu_api_key_aqui"
        )
        if is_valid:
            return "ok", "vt_api_ok"
        return "error", "vt_api_missing"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Realiza la consulta HTTP asíncrona blindando el manejo de excepciones de red."""
        if not self.api_key or self.api_key.lower() == "tu_api_key_aqui":
            callback(
                "[-] Error crítico: No se encontró VIRUSTOTAL_API_KEY en el archivo .env\n"
            )
            return {"status": "error", "error": "Missing API Key"}

        callback(f"[*] Iniciando análisis en VirusTotal para: {target}\n")

        is_ip: bool = bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target))
        endpoint: str = f"ip_addresses/{target}" if is_ip else f"domains/{target}"
        url: str = f"https://www.virustotal.com/api/v3/{endpoint}"

        headers: dict[str, str] = {
            "accept": "application/json",
            "x-apikey": self.api_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response: httpx.Response = await client.get(
                    url, headers=headers, timeout=10.0
                )
                response.raise_for_status()

            data: dict[str, Any] = response.json()
            stats: dict[str, int] = (
                data.get("data", {})
                .get("attributes", {})
                .get("last_analysis_stats", {})
            )
            owner: str = (
                data.get("data", {})
                .get("attributes", {})
                .get("as_owner", "Desconocido")
                if is_ip
                else "N/A"
            )

            callback("[+] Resultados obtenidos de los motores de análisis:\n")
            callback(f"    - 🔴 Malicioso:   {stats.get('malicious', 0)}\n")
            callback(f"    - 🟠 Sospechoso:  {stats.get('suspicious', 0)}\n")
            callback(f"    - 🟢 Inofensivo:  {stats.get('harmless', 0)}\n")
            callback(f"    - ⚪ Indetectado: {stats.get('undetected', 0)}\n")

            if is_ip:
                callback(f"    - 🏢 Propietario (ASN): {owner}\n")

            callback("\n[+] Búsqueda en VirusTotal finalizada.\n")
            return {"status": "success", "target": target, "stats": stats}

        except httpx.HTTPStatusError as err:
            status_code: int = err.response.status_code
            logger.error(
                "Error de estado HTTP %d devuelto por VirusTotal: %s", status_code, err
            )
            if status_code == 401:
                callback(
                    "[-] Error 401: Tu API Key es inválida, falta o ha caducado.\n"
                )
            elif status_code == 404:
                callback(
                    "[-] Error 404: Este objetivo nunca ha sido escaneado en VirusTotal.\n"
                )
            elif status_code == 429:
                callback(
                    "[-] Error 429: Has superado el límite de peticiones gratuitas por minuto.\n"
                )
            else:
                callback(f"[-] Error de API inesperado: Código HTTP {status_code}\n")
            return {"status": "error", "error": f"HTTP {status_code}"}

        except httpx.TimeoutException as err:
            logger.error(
                "Tiempo de espera agotado al conectar con la API de VirusTotal: %s", err
            )
            callback(
                "[-] Error de red: Tiempo de espera agotado al conectar con VirusTotal.\n"
            )
            return {"status": "error", "error": "timeout"}

        except httpx.RequestError as err:
            logger.error(
                "Excepción de transporte/red al conectar con VirusTotal: %s", err
            )
            callback(f"[-] Error de red crítico al contactar VirusTotal: {err}\n")
            return {"status": "error", "error": str(err)}
