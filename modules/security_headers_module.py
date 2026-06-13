import logging
from typing import Any, Callable

import httpx

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)


class SecurityHeadersModule(BaseModule):
    """Módulo OSINT para el análisis y auditoría de cabeceras HTTP de seguridad pasivas."""

    def __init__(self) -> None:
        # Sincronizado con la clave exacta de mapeo del archivo main.py
        super().__init__("SecurityHeaders")
        self.description: str = (
            "Analiza y verifica las cabeceras HTTP de seguridad de un servidor"
        )

    def check_health(self) -> tuple[str, str]:
        """Comprueba el estado de salud y dependencias del analizador de cabeceras."""
        return "ok", "headers_ok"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Evalúa las directivas de seguridad inyectadas en la respuesta HTTP del servidor."""
        callback(f"[*] Iniciando análisis de cabeceras de seguridad para: {target}\n")

        target = target.strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            target = f"https://{target}"

        callback(f"[*] Evaluando cabeceras en: {target}\n")

        headers_req: dict[str, str] = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

        response: httpx.Response | None = None

        # verify=False permite auditar entornos pre-producción con SSL autofirmados o rotos
        callback(
            "[*] Nota: Verificación SSL desactivada para alcanzar todos los servidores.\n"
        )

        try:
            async with httpx.AsyncClient(verify=False) as client:
                try:
                    response = await client.head(
                        target, headers=headers_req, follow_redirects=True, timeout=10.0
                    )
                    response.raise_for_status()
                except (httpx.RequestError, httpx.HTTPStatusError) as err:
                    logger.warning(
                        "Petición HTTP HEAD fallida contra '%s': %s. Reintentando método GET...",
                        target,
                        err,
                    )
                    callback(
                        "[*] Petición HEAD falló o fue rechazada, reintentando con GET...\n"
                    )

                    response = await client.get(
                        target, headers=headers_req, follow_redirects=True, timeout=10.0
                    )
                    response.raise_for_status()

                if response:
                    callback(
                        f"[+] Conexión exitosa, procesando respuesta HTTP {response.status_code}...\n\n"
                    )

                    server: str = response.headers.get("Server", "Oculto/Desconocido")
                    hsts: str | None = response.headers.get("Strict-Transport-Security")
                    csp: str | None = response.headers.get("Content-Security-Policy")
                    x_frame: str | None = response.headers.get("X-Frame-Options")
                    x_content_type: str | None = response.headers.get(
                        "X-Content-Type-Options"
                    )

                    callback(f"[*] Software del Servidor detectado: {server}\n\n")

                    if hsts:
                        callback("    [+] Strict-Transport-Security (HSTS): Presente\n")
                    else:
                        callback(
                            "    [!] Strict-Transport-Security (HSTS): Faltante (Vulnerable)\n"
                        )

                    if csp:
                        callback("    [+] Content-Security-Policy (CSP): Presente\n")
                    else:
                        callback(
                            "    [!] Content-Security-Policy (CSP): Faltante (Vulnerable)\n"
                        )

                    if x_frame:
                        callback(
                            f"    [+] X-Frame-Options (Clickjacking): Presente [{x_frame}]\n"
                        )
                    else:
                        callback(
                            "    [!] X-Frame-Options (Clickjacking): Faltante (Vulnerable)\n"
                        )

                    if x_content_type:
                        callback(
                            f"    [+] X-Content-Type-Options (Sniffing): Presente [{x_content_type}]\n"
                        )
                    else:
                        callback(
                            "    [!] X-Content-Type-Options (Sniffing): Faltante (Vulnerable)\n"
                        )

                    callback("\n[+] Análisis de cabeceras de seguridad finalizado.\n")
                    return {"status": "success", "target": target}

        except httpx.HTTPStatusError as err:
            logger.error(
                "El servidor remoto denegó la conexión final arrojando código HTTP %d: %s",
                err.response.status_code,
                err,
            )
            callback(
                f"[-] El servidor respondió con un error HTTP crítico: Código {err.response.status_code}\n"
            )
            return {
                "status": "error",
                "error": f"HTTP_Status_{err.response.status_code}",
            }

        except httpx.TimeoutException as err:
            logger.warning(
                "Expiró el tiempo límite de conexión con el host perimetral: %s", err
            )
            callback(
                "[-] Error de red: Tiempo de espera agotado al conectar con el servidor.\n"
            )
            return {"status": "error", "error": "timeout"}

        except httpx.RequestError as err:
            logger.error(
                "Error de transporte de datos o DNS al auditar las cabeceras: %s", err
            )
            callback(f"[-] Error de red al intentar conectar con el servidor: {err}\n")
            return {"status": "error", "error": str(err)}

        return {"status": "error", "error": "unknown_execution_failure"}
