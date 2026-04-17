import asyncio
import os
import sys
import psutil

from core.base_module import BaseModule


class PhoneInfogaModule(BaseModule):
    """
    Módulo que ejecuta el binario externo phoneinfoga (Go binary).
    Lanza un subproceso asíncrono, captura stdout/stderr en tiempo real
    e inyecta cada línea en la consola de la GUI.
    El PID del proceso hijo se registra para permitir la cancelación
    limpia a través del botón 'Detener' (vía psutil).
    """

    name = "PhoneInfoga"

    def __init__(self):
        self._process: asyncio.subprocess.Process | None = None

    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando PhoneInfoga para el número: {target}\n")

        # --- Localizar el binario ---
        # Busca primero en la raíz del proyecto (junto a main.py),
        # luego en el PATH del sistema.
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        binary_name = "phoneinfoga.exe" if sys.platform == "win32" else "phoneinfoga"
        local_binary = os.path.join(project_root, binary_name)

        if os.path.isfile(local_binary):
            executable = local_binary
        else:
            # Fallback: intentar desde el PATH del sistema
            executable = binary_name

        callback(f"[*] Usando ejecutable: {executable}\n")
        callback(f"[*] Comando: {executable} scan -n {target} --disable googlesearch\n\n")

        try:
            self._process = await asyncio.create_subprocess_exec(
                executable, "scan", "-n", target, "--disable", "googlesearch",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            callback(
                f"[-] Error: No se encontró el ejecutable '{binary_name}'.\n"
                f"    Asegúrate de que el binario esté en la raíz del proyecto "
                f"o en el PATH del sistema.\n"
            )
            return {"status": "error", "error": "binary_not_found"}
        except Exception as e:
            callback(f"[-] Error al lanzar PhoneInfoga: {e}\n")
            return {"status": "error", "error": str(e)}

        callback(f"[+] Proceso iniciado (PID: {self._process.pid})\n\n")

        async def _stream_reader(stream, prefix: str = ""):
            """Lee líneas de un stream asíncrono y las envía al callback."""
            while True:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    callback(f"{prefix}{line}\n")

        try:
            # Leer stdout y stderr concurrentemente
            await asyncio.gather(
                _stream_reader(self._process.stdout),
                _stream_reader(self._process.stderr, prefix="[stderr] "),
            )
            await self._process.wait()
        except asyncio.CancelledError:
            # El usuario pulsó 'Detener': matar el proceso hijo y sus descendientes
            callback("\n[!] Cancelación solicitada — terminando proceso PhoneInfoga...\n")
            self._kill_process_tree()
            raise  # Re-lanzar para que _async_module_execution lo gestione
        finally:
            self._process = None

        callback("\n[+] PhoneInfoga finalizado.\n")
        return {"status": "success", "target": target}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _kill_process_tree(self):
        """Mata el proceso hijo y todos sus descendientes usando psutil."""
        if self._process is None:
            return
        pid = self._process.pid
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
        except psutil.NoSuchProcess:
            pass
        except Exception:
            pass
