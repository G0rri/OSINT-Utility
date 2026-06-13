import asyncio
import logging
import os
import shutil
from typing import Any, Callable

import psutil

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)


class PhoneInfogaModule(BaseModule):
    """Módulo que ejecuta el binario externo phoneinfoga (Go binary) de forma asíncrona."""

    def __init__(self) -> None:
        # Registramos el nombre del módulo de cara a la clase abstracta
        super().__init__("PhoneInfoga")
        self._process: asyncio.subprocess.Process | None = None

    def check_health(self) -> tuple[str, str]:
        """Comprueba el estado del binario y la presencia de las llaves de API."""
        project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        binary_name: str = "phoneinfoga"
        local_binary: str = os.path.join(project_root, binary_name)

        has_binary: bool = (
            os.path.isfile(local_binary) or shutil.which(binary_name) is not None
        )
        if not has_binary:
            return "error", "pi_binary_missing"

        numverify: str | None = os.getenv("NUMVERIFY_API_KEY")
        apilayer: str | None = os.getenv("APILAYER_KEY")

        def is_valid(key: str | None) -> bool:
            return bool(key and key.lower() != "tu_api_key_aqui")

        if not is_valid(numverify) and not is_valid(apilayer):
            return "warning", "pi_api_missing"

        return "ok", "pi_ok"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Lanza de forma segura la ejecución del binario asíncrono."""
        callback(f"[*] Iniciando PhoneInfoga para el número: {target}\n")

        project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        binary_name: str = "phoneinfoga"
        local_binary: str = os.path.join(project_root, binary_name)

        executable: str = local_binary if os.path.isfile(local_binary) else binary_name

        callback(f"[*] Usando ejecutable: {executable}\n")
        callback(
            f"[*] Comando: {executable} scan -n {target} --disable googlesearch\n\n"
        )

        try:
            # shell=False implícito por el uso de create_subprocess_exec con paso de argumentos en lista
            self._process = await asyncio.create_subprocess_exec(
                executable,
                "scan",
                "-n",
                target,
                "--disable",
                "googlesearch",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as err:
            logger.error("No se localizó el ejecutable de PhoneInfoga: %s", err)
            callback(
                f"[-] Error: No se encontró el ejecutable '{binary_name}'.\n"
                f"    Asegúrate de que el binario esté en la raíz del proyecto "
                f"o en el PATH del sistema.\n"
            )
            return {"status": "error", "error": "binary_not_found"}
        except (OSError, RuntimeError) as err:
            logger.error("Fallo del sistema operativo al invocar PhoneInfoga: %s", err)
            callback(f"[-] Error al lanzar PhoneInfoga: {err}\n")
            return {"status": "error", "error": str(err)}

        callback(f"[+] Proceso iniciado (PID: {self._process.pid})\n\n")

        # Aseguramos al linter la existencia de las tuberías E/S
        if self._process.stdout is None or self._process.stderr is None:
            logger.error(
                "No se pudieron inicializar los canales E/S del subproceso PhoneInfoga."
            )
            return {"status": "error", "error": "io_pipes_failed"}

        async def _stream_reader(
            stream: asyncio.StreamReader, prefix: str = ""
        ) -> None:
            """Lee líneas de un stream asíncrono y las envía al callback."""
            while True:
                line_bytes: bytes = await stream.readline()
                if not line_bytes:
                    break
                line: str = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    callback(f"{prefix}{line}\n")

        try:
            await asyncio.gather(
                _stream_reader(self._process.stdout),
                _stream_reader(self._process.stderr, prefix="[stderr] "),
            )
            await self._process.wait()
        except asyncio.CancelledError:
            callback(
                "\n[!] Cancelación solicitada — terminando proceso PhoneInfoga...\n"
            )
            self._kill_process_tree()
            raise
        finally:
            self._process = None

        callback("\n[+] PhoneInfoga finalizado.\n")
        return {"status": "success", "target": target}

    def _kill_process_tree(self) -> None:
        """Mata el proceso hijo y todos sus descendientes usando psutil evitando fugas."""
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
                        "Permiso denegado para terminar el subproceso hijo PID %d.",
                        child.pid,
                    )
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                logger.error(
                    "Permiso denegado para terminar el proceso padre PID %d.", pid
                )
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            logger.error("Acceso denegado a la telemetría del PID raíz %d.", pid)
