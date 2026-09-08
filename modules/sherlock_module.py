import asyncio
import logging
import re
import sys
from collections.abc import Callable
from typing import Any

import psutil

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)

_URL_RE: re.Pattern[str] = re.compile(r"https?://[^\s]+")


class SherlockModule(BaseModule):
    """Módulo OSINT para el rastreo de nombres de usuario mediante Sherlock."""

    def __init__(self) -> None:
        super().__init__("Sherlock")
        self._process: asyncio.subprocess.Process | None = None

    def check_health(self) -> tuple[str, str]:
        """Comprueba si la dependencia de ejecución de Sherlock está presente en el entorno."""
        import importlib.util

        is_installed: bool = (
            importlib.util.find_spec("sherlock_project") is not None
            or importlib.util.find_spec("sherlock") is not None
        )
        if is_installed:
            return "ok", "sherlock_ok"
        return "error", "sherlock_missing"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Lanza de forma asíncrona y aislada el escaneo de sitios web."""
        callback(f"[*] Iniciando búsqueda Sherlock para el usuario: {target}\n")

        # Los perfiles se recogen mientras se transmiten, para devolverlos y que
        # el caso pueda encadenarlos sin volver a leer la consola.
        perfiles: list[str] = []

        cmd: list[str] = [
            sys.executable,
            "-m",
            "sherlock_project",
            target,
            "--print-found",
            "--timeout",
            "3",
            "--no-txt",
        ]

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Verificación de tipo estricta exigida por el linter
            if self._process.stdout is None or self._process.stderr is None:
                raise RuntimeError(
                    "No se pudieron inicializar las tuberías de comunicación E/S."
                )

            async def _stream_reader(
                stream: asyncio.StreamReader, prefix: str = "", recoger: bool = False
            ) -> None:
                while True:
                    line_bytes: bytes = await stream.readline()
                    if not line_bytes:
                        break
                    line: str = line_bytes.decode("utf-8", errors="replace").rstrip(
                        "\r\n"
                    )
                    if line:
                        if recoger:
                            self._recoger_perfil(line, perfiles)
                        callback(f"{prefix}{line}\n")
                        await asyncio.sleep(0.001)

            # Consumo simultáneo seguro de flujos de datos
            await asyncio.gather(
                _stream_reader(self._process.stdout, prefix="    ", recoger=True),
                _stream_reader(self._process.stderr, prefix="    [!] "),
            )
            await self._process.wait()

        except asyncio.CancelledError:
            callback("\n[!] Búsqueda de Sherlock detenida por el usuario...\n")
            self._kill_process_tree()
            raise
        except (OSError, RuntimeError) as err:
            logger.error("Error crítico en subproceso Sherlock: %s", err)
            callback(f"[-] Error al lanzar Sherlock: {err}\n")
            return {"status": "error", "error": str(err)}
        finally:
            self._process = None

        callback("\n[+] Búsqueda en Sherlock finalizada.\n")
        return {"status": "success", "target": target, "profiles": perfiles}

    @staticmethod
    def _recoger_perfil(linea: str, perfiles: list[str]) -> None:
        """Extrae la URL de perfil de una línea de acierto de Sherlock.

        Sherlock imprime los aciertos como `[+] Sitio: https://...`. Solo se
        recoge la URL, que es el dato encadenable; el texto de la línea sigue
        yendo a la consola sin alterar.
        """
        if "[+]" not in linea:
            return
        match = _URL_RE.search(linea)
        if match:
            url: str = match.group()
            if url not in perfiles:
                perfiles.append(url)

    def _kill_process_tree(self) -> None:
        """Termina de forma segura el árbol de procesos para evitar hilos zombies."""
        if self._process is None:
            return
        pid: int = self._process.pid
        try:
            parent: psutil.Process = psutil.Process(pid)
            children: list[psutil.Process] = parent.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
                except psutil.AccessDenied:
                    logger.error(
                        "Permiso denegado para mitigar PID hijo: %d", child.pid
                    )
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                logger.error("Permiso denegado para mitigar PID padre: %d", pid)
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            logger.error("Acceso denegado a la telemetría del PID: %d", pid)
