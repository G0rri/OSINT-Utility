import asyncio
import logging
import os
import urllib.parse
from typing import Any, Callable, List

from core.base_module import BaseModule

# Configuración del registrador de trazas nativo profesional
logger = logging.getLogger(__name__)


class PhoneInfogaModule(BaseModule):
    def __init__(self) -> None:
        super().__init__("PhoneInfoga")
        self._enable_google_search: bool = False

    def toggle_google_search(self, enable: bool) -> None:
        """Configura de forma segura si el escáner ejecutará Google Dorks."""
        self._enable_google_search = enable
        logger.debug(f"PhoneInfoga: google_search establecido en {enable}")

    def _get_executable_path(self) -> str:
        """Calcula la ruta absoluta del binario de forma dinámica y resiliente.

        Comprueba primero la raíz del proyecto y luego la subcarpeta bin.
        """
        base_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Prioridad 1: Buscar directamente en la raíz del proyecto
        root_path: str = os.path.join(base_dir, "phoneinfoga")
        if os.path.exists(root_path):
            return root_path

        # Prioridad 2: Buscar en la subcarpeta bin (arquitectura estándar)
        bin_path: str = os.path.join(base_dir, "bin", "phoneinfoga")
        return bin_path

    def _generate_human_variants(self, target: str) -> List[str]:
        """Genera variaciones comunes de escritura manual basándose en el objetivo."""
        clean: str = "".join([c for c in target if c.isdigit() or c == "+"])
        digits: str = clean.lstrip("+")
        variants: List[str] = []

        if len(digits) >= 9:
            local: str = digits[-9:]
            prefix: str = digits[:-9]

            # Formatos puramente locales sin código de país
            variants.append(local)
            variants.append(
                f"{local[:3]} {local[3:5]} {local[5:7]} {local[7:]}"
            )  # Ej: 967 83 17 84
            variants.append(f"{local[:3]} {local[3:6]} {local[6:]}")  # Ej: 967 831 784
            variants.append(f"{local[:3]}-{local[3:6]}-{local[6:]}")  # Ej: 967-831-784
            variants.append(
                f"{local[:3]}-{local[3:5]}-{local[5:7]}-{local[7:]}"
            )  # Ej: 967-83-17-84

            # Formatos compuestos con prefijo internacional
            if prefix:
                variants.append(f"+{prefix}{local}")
                variants.append(
                    f"+{prefix} {local[:3]} {local[3:5]} {local[5:7]} {local[7:]}"
                )
                variants.append(f"00{prefix} {local}")
        else:
            variants.append(digits)

        return sorted(list(set(variants)))

    def _build_custom_dorks(self, target: str) -> str:
        """Construye un bloque de texto formateado con enlaces OSINT mutados avanzados."""
        variants: List[str] = self._generate_human_variants(target)
        lines: List[str] = [
            "\n" + "=" * 60,
            " 🔍 VARIANTES DE BÚSQUEDA HUMANA AVANZADA (PYTHON EXTRA)",
            "=" * 60,
            "[*] Generando consultas recursivas para evadir formatos estrictos...\n",
        ]

        for variant in variants:
            lines.append(f"[+] Formato Detectado: '{variant}'")

            # 1. Dork de Google General (Texto exacto)
            q_gen: str = f'"{variant}"'
            url_gen: str = (
                f"https://www.google.com/search?q={urllib.parse.quote_plus(q_gen)}"
            )
            lines.append(f"  -> Google General: {url_gen}")

            # 2. Dork de Redes Sociales (Aislado)
            q_soc: str = f'"{variant}" (site:facebook.com OR site:instagram.com OR site:twitter.com OR site:linkedin.com)'
            url_soc: str = (
                f"https://www.google.com/search?q={urllib.parse.quote_plus(q_soc)}"
            )
            lines.append(f"  -> Redes Sociales: {url_soc}")

            # 3. Dork de Fugas y Spam (Foros / Listas de spam)
            q_spam: str = f'"{variant}" (site:listaspam.com OR site:milanuncios.com OR site:wallapop.com OR "pastebin")'
            url_spam: str = (
                f"https://www.google.com/search?q={urllib.parse.quote_plus(q_spam)}"
            )
            lines.append(f"  -> Fugas y Clasificados: {url_spam}\n")

        return "\n".join(lines) + "\n"

    def check_health(self) -> tuple[str, str]:
        """Verifica de forma dinámica la presencia y permisos del ejecutable."""
        executable_path: str = self._get_executable_path()

        if os.path.exists(executable_path):
            if os.access(executable_path, os.X_OK):
                return ("ok", "Listo")
            return ("warning", "Faltan permisos de ejecución (chmod +x)")
        return ("error", "Falta binario ejecutable de PhoneInfoga en el proyecto")

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Ejecuta el escaneo asíncrono e inyecta dorks condicionalmente."""
        logger.info(f"Iniciando escaneo de PhoneInfoga para el objetivo: {target}")

        executable_path: str = self._get_executable_path()
        cmd: List[str] = [executable_path, "scan", "-n", target]

        if not self._enable_google_search:
            cmd.extend(["-D", "googlesearch"])

        resultado: dict[str, Any] = {"status": "failed", "raw_output": ""}

        try:
            # Ejecución segura mediante paso de argumentos en lista (shell=False)
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            stdout_str = stdout.decode("utf-8", errors="ignore") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="ignore") if stderr else ""

            if stdout_str:
                callback(stdout_str)
                resultado["raw_output"] = stdout_str
                resultado["status"] = "success"

            if stderr_str:
                logger.warning(f"PhoneInfoga emitió una traza secundaria: {stderr_str}")
                callback(f"\n[!] Traza del sistema: {stderr_str}")
                if not resultado["raw_output"]:
                    resultado["raw_output"] = stderr_str

            # 🛠️ CORRECCIÓN CRÍTICA: Los dorks extras ahora solo se calculan e inyectan si el usuario activó la opción
            if self._enable_google_search:
                custom_dorks: str = self._build_custom_dorks(target)
                callback(custom_dorks)
                resultado["raw_output"] += custom_dorks

        except FileNotFoundError:
            logger.error(
                f"El ejecutable de PhoneInfoga no se encontró en: {executable_path}"
            )
            callback(
                f"❌ Error Crítico: No se pudo localizar el binario en: {executable_path}"
            )
            resultado["error"] = "Binario no encontrado"
        except asyncio.CancelledError:
            logger.info(
                "El proceso asíncrono de PhoneInfoga ha sido cancelado por el usuario."
            )
            resultado["status"] = "cancelled"
            raise
        except OSError as error:
            logger.critical(f"Fallo de bajo nivel en el sistema operativo: {error}")
            callback(f"❌ Error interno de ejecución en el sistema: {error}")
            resultado["error"] = str(error)

        return resultado
