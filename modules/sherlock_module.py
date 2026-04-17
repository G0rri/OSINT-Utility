import asyncio
import io
import contextlib
import sys
import signal

from core.base_module import BaseModule

class SherlockModule(BaseModule):
    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando búsqueda Sherlock para el usuario: {target}\n")
        
        try:
            try:
                from sherlock import sherlock as sherlock_core
            except ImportError:
                from sherlock_project import sherlock as sherlock_core
        except ImportError:
            callback("[-] Error: Sherlock no se encuentra instalado.\n")
            return {"status": "error", "error": "Not installed"}

        # Respaldos
        original_argv = sys.argv
        original_signal = signal.signal
        
        # Inyección de argumentos CLI
        sys.argv = ["sherlock", target, "--print-found", "--timeout", "3", "--output", "NUL"] 

        output_buffer = io.StringIO()
        
        try:
            # Monkey-patching: Desactivamos el registro de señales para evitar el crasheo en hilos secundarios
            signal.signal = lambda *args, **kwargs: None
            
            with contextlib.redirect_stdout(output_buffer):
                if asyncio.iscoroutinefunction(sherlock_core.main):
                    await sherlock_core.main()
                else:
                    await asyncio.to_thread(sherlock_core.main)
        except Exception as e:
            if not isinstance(e, SystemExit):
                callback(f"[-] Error interno en Sherlock: {e}\n")
                return {"status": "error", "error": str(e)}
        finally:
            # Restauración absoluta
            sys.argv = original_argv
            signal.signal = original_signal

        raw_output = output_buffer.getvalue()
        for line in raw_output.splitlines():
            if line.strip(): 
                callback(f"    {line}\n")
                await asyncio.sleep(0.005)

        callback("\n[+] Búsqueda en Sherlock finalizada.\n")
        return {"status": "success", "target": target, "raw_output": raw_output}