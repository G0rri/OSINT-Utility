import asyncio
import logging
import socket
from typing import Any, Callable

import httpx

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)


class PortScannerModule(BaseModule):
    """Módulo OSINT para el mapeo pasivo de puertos perimetrales mediante Shodan InternetDB."""

    def __init__(self) -> None:
        super().__init__("PortScanner")

    def check_health(self) -> tuple[str, str]:
        """Verifica el estado de salud y disponibilidad del escáner de puertos."""
        return "ok", "ports_ok"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Resuelve el host e interroga pasivamente la base de datos de Shodan."""
        callback(
            f"[*] Iniciando escaneo de puertos (Shodan InternetDB) para: {target}\n"
        )
        try:
            # Resolvemos el dominio delegando al pool de hilos de forma asíncrona para no congelar la UI
            ip: str = await asyncio.to_thread(socket.gethostbyname, target)
            callback(f"[*] Objetivo resuelto a la IP: {ip}\n")
        except socket.gaierror as err:
            logger.error(
                "Error de resolución DNS al mapear el host '%s': %s", target, err
            )
            callback(
                f"[-] Error de DNS: No se pudo resolver '{target}'. Verifica la ortografía o tu conexión.\n"
            )
            return {"status": "error", "error": "DNS resolution failed"}
        except OSError as err:
            logger.error(
                "Fallo del sistema de red/sockets al resolver el host '%s': %s",
                target,
                err,
            )
            callback(f"[-] Error inesperado del sistema al resolver el host: {err}\n")
            return {"status": "error", "error": str(err)}

        url: str = f"https://internetdb.shodan.io/{ip}"

        async with httpx.AsyncClient() as client:
            try:
                response: httpx.Response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data: dict[str, Any] = response.json()
                    ports: list[int] = data.get("ports", [])
                    if ports:
                        callback("[+] Puertos abiertos detectados externamente:\n")
                        for p in ports:
                            callback(f"    - Puerto {p} [ABIERTO]\n")
                    else:
                        callback(
                            "[-] No se detectaron puertos abiertos en la base de datos de Shodan.\n"
                        )
                elif response.status_code == 404:
                    callback(
                        "[-] Esta IP no está indexada en Shodan (Probablemente no expone puertos).\n"
                    )
                else:
                    callback(
                        f"[-] Error de la API de Shodan: Código HTTP {response.status_code}\n"
                    )

            except httpx.TimeoutException as err:
                logger.warning(
                    "Tiempo de espera agotado con la API de Shodan InternetDB: %s", err
                )
                callback(
                    "[-] Error de red: Tiempo de espera agotado al consultar la base de datos de Shodan.\n"
                )
            except httpx.RequestError as err:
                logger.error(
                    "Error de transporte de red al interrogar Shodan InternetDB: %s",
                    err,
                )
                callback(f"[-] Error de red al consultar Shodan: {err}\n")

        callback("\n[+] Escaneo finalizado.\n")
        return {"status": "success"}
