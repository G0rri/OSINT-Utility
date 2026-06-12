import asyncio
import sys
import psutil
from core.base_module import BaseModule

class SherlockModule(BaseModule):
    name = "Sherlock"

    def __init__(self):
        self._process = None

    def check_health(self) -> tuple[str, str]:
        import importlib.util
        is_installed = importlib.util.find_spec("sherlock_project") is not None or importlib.util.find_spec("sherlock") is not None
        if is_installed:
            return "none", ""
        return "error", "sherlock_missing"

    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando búsqueda Sherlock para el usuario: {target}\n")
        
        # Lanzar sherlock como proceso usando el módulo python
        # El timeout es para acotar cada petición de sitio, --no-txt evita el archivo generado.
        cmd = [sys.executable, "-m", "sherlock_project", target, "--print-found", "--timeout", "3", "--no-txt"]
        
        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            async def _stream_reader(stream, prefix=""):
                while True:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break
                    line = line_bytes.decode('utf-8', errors='replace').rstrip('\r\n')
                    if line:
                        callback(f"{prefix}{line}\n")
                        await asyncio.sleep(0.001)
                        
            # Leer concurremente
            await asyncio.gather(
                _stream_reader(self._process.stdout, prefix="    "),
                _stream_reader(self._process.stderr, prefix="    [!] ")
            )
            await self._process.wait()
            
        except asyncio.CancelledError:
            callback("\n[!] Búsqueda de Sherlock detenida por el usuario...\n")
            self._kill_process_tree()
            raise
        except Exception as e:
            callback(f"[-] Error al lanzar Sherlock: {e}\n")
            return {"status": "error", "error": str(e)}
        finally:
            self._process = None

        callback("\n[+] Búsqueda en Sherlock finalizada.\n")
        return {"status": "success", "target": target}

    def _kill_process_tree(self):
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