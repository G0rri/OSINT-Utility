import asyncio
import logging
import os
import subprocess
import sys
from typing import Any, Callable

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)


class HoleheModule(BaseModule):
    """Módulo OSINT para la verificación pericial de correos mediante Holehe."""

    def __init__(self) -> None:
        super().__init__("Holehe")

    def check_health(self) -> tuple[str, str]:
        """Verifica la existencia de la librería holehe instalada en el entorno virtual."""
        import importlib.util

        is_installed: bool = importlib.util.find_spec("holehe") is not None
        if is_installed:
            return "ok", "holehe_ok"
        return "error", "holehe_missing"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Ejecuta el script de auto-aislamiento de Holehe sin bloquear el bucle de la UI."""
        callback(f"[*] Iniciando búsqueda Holehe para el email: {target}\n")

        executable: str = sys.executable
        cmd: list[str] = [executable]

        if not getattr(sys, "frozen", False):
            main_script: str = os.path.abspath(sys.argv[0])
            cmd.append(main_script)

        cmd.extend(["--run-holehe", target])

        try:

            def run_process() -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                )

            process: subprocess.CompletedProcess[str] = await asyncio.to_thread(
                run_process
            )

            if process.stdout:
                for line in process.stdout.splitlines():
                    if line.strip():
                        callback(f"    {line}\n")
                        await asyncio.sleep(0.005)

            if process.stderr:
                for line in process.stderr.splitlines():
                    if line.strip() and "UserWarning" not in line:
                        callback(f"    [!] {line}\n")

            callback("\n[+] Búsqueda en Holehe finalizada.\n")
            return {"status": "success", "target": target, "raw_output": process.stdout}

        except (OSError, subprocess.SubprocessError) as err:
            logger.error(
                "Error crítico interno ejecutando subproceso de Holehe: %s", err
            )
            callback(
                f"[-] Ocurrió un error crítico lanzando el proceso de Holehe: {err}\n"
            )
            return {"status": "error", "error": str(err)}
