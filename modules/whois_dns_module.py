import asyncio
import logging
import socket
from typing import Any, Callable

import dns.asyncresolver
import dns.exception
import dns.resolver
import whois

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)


class WhoisDnsModule(BaseModule):
    """Módulo nativo asíncrono para recolección de información WHOIS y resolución DNS."""

    def __init__(self) -> None:
        # Sincronizado con la clave exacta "WHOIS" mapeada en el diccionario de main.py
        super().__init__("WHOIS")

    def check_health(self) -> tuple[str, str]:
        """Comprueba la salud operacional del módulo de resolución de dominios."""
        return "ok", "whois_ok"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Ejecuta la consulta pericial WHOIS delegada y enumera registros DNS sin bloquear la UI."""
        callback(f"[*] Iniciando recolección WHOIS y DNS para el dominio: {target}\n")

        results: dict[str, Any] = {"target": target, "whois": {}, "dns": {}}

        # ----- 1. SECCIÓN WHOIS -----
        callback("[*] Consultando información WHOIS...\n")
        try:
            # whois.whois realiza llamadas bloqueantes al puerto lógico 43.
            # Se delega de forma segura al pool de hilos de asyncio para mantener la fluidez de la GUI.
            w: Any = await asyncio.to_thread(whois.whois, target)

            if not w.domain_name:
                callback(
                    "[-] WHOIS: No se encontró información registrada o el dominio está disponible.\n"
                )
            else:
                registrar: str = w.registrar or "Desconocido"
                creation: Any = w.creation_date
                expiration: Any = w.expiration_date

                if isinstance(creation, list):
                    creation = creation[0]
                if isinstance(expiration, list):
                    expiration = expiration[0]

                name_servers: Any = w.name_servers or []
                if isinstance(name_servers, str):
                    name_servers = [name_servers]

                callback("[+] Resultados WHOIS:\n")
                callback(f"    - 🏢 Registrador: {registrar}\n")
                callback(f"    - 📅 Creación:    {creation}\n")
                callback(f"    - ⏰ Expiración:  {expiration}\n")

                if name_servers:
                    callback("    - 🌐 Name Servers:\n")
                    for ns in name_servers:
                        callback(f"       • {ns}\n")

                results["whois"] = {
                    "registrar": registrar,
                    "creation": str(creation),
                    "expiration": str(expiration),
                    "name_servers": name_servers,
                }
        except (OSError, socket.error) as err:
            logger.error(
                "Error de socket o tiempo de espera agotado al conectar al servidor WHOIS: %s",
                err,
            )
            callback(f"[-] Error de red al consultar el servidor WHOIS: {err}\n")
        except AttributeError as err:
            logger.error(
                "Error de análisis estructural en el objeto de respuesta WHOIS: %s", err
            )
            callback(
                "[-] Error de formato: La respuesta del servidor WHOIS no pudo ser procesada.\n"
            )

        # ----- 2. SECCIÓN DNS -----
        callback("\n[*] Resolviendo registros DNS...\n")

        resolver: dns.asyncresolver.Resolver = dns.asyncresolver.Resolver()
        records_to_check: list[str] = ["A", "MX", "TXT"]

        for record_type in records_to_check:
            try:
                answers: Any = await resolver.resolve(target, record_type)

                callback(f"[+] Registros {record_type}:\n")
                record_list: list[str] = []
                for rdata in answers:
                    text_rdata: str = rdata.to_text()
                    callback(f"    - {text_rdata}\n")
                    record_list.append(text_rdata)

                results["dns"][record_type] = record_list

            except dns.resolver.NoAnswer:
                callback(
                    f"[-] Registros {record_type}: No se encontraron respuestas para este tipo.\n"
                )
            except dns.resolver.NXDOMAIN:
                logger.warning(
                    "El dominio primario '%s' arrojó un estado NXDOMAIN.", target
                )
                callback("[-] Error: El dominio introducido no existe (NXDOMAIN).\n")
                break
            except dns.resolver.NoNameservers:
                logger.error(
                    "Los servidores de nombres autoritativos fallaron profundamente para '%s'.",
                    target,
                )
                callback(
                    "[-] Error: Los Servidores DNS no respondieron o están fallando profundamente.\n"
                )
                break
            except dns.exception.DNSException as err:
                logger.error(
                    "Excepción interna de dnspython al resolver la entrada %s: %s",
                    record_type,
                    err,
                )
                callback(
                    f"[-] Error de DNS al resolver la entrada {record_type}: {err}\n"
                )
            except OSError as err:
                logger.error(
                    "Error del sistema operativo/red en la resolución DNS de %s: %s",
                    record_type,
                    err,
                )
                callback(
                    f"[-] Error de red del sistema en la entrada {record_type}: {err}\n"
                )

            await asyncio.sleep(0.01)

        callback("\n[+] Análisis local de WHOIS y DNS finalizado.\n")
        results["status"] = "success"

        return results
