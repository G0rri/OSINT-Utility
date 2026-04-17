import asyncio
import sys
import os
import subprocess
from core.base_module import BaseModule

class HoleheModule(BaseModule):
    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando búsqueda Holehe para el email: {target}\n")
        
        # Preparamos el comando de auto-ejecución
        executable = sys.executable
        cmd = [executable]
        
        if not getattr(sys, 'frozen', False):
            main_script = os.path.abspath(sys.argv[0])
            cmd.append(main_script)
            
        cmd.extend(["--run-holehe", target])
        
        try:
            # Envolvemos subprocess.run en to_thread para no congelar la GUI.
            # CREATE_NO_WINDOW es vital en Windows para que no salte una terminal extra al compilar en .exe
            def run_process():
                flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                return subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8', 
                    errors='replace', 
                    creationflags=flags
                )

            process = await asyncio.to_thread(run_process)
            
            # Leemos la salida generada
            if process.stdout:
                for line in process.stdout.splitlines():
                    if line.strip():
                        callback(f"    {line}\n")
                        await asyncio.sleep(0.005)
                        
            if process.stderr:
                for line in process.stderr.splitlines():
                    if line.strip() and "UserWarning" not in line:
                        callback(f"    [!] {line}\n")
            
        except Exception as e:
            callback(f"[-] Ocurrió un error crítico lanzando el proceso de Holehe: {e}\n")
            return {"status": "error", "error": str(e)}

        callback("\n[+] Búsqueda en Holehe finalizada.\n")
        return {"status": "success", "target": target, "raw_output": process.stdout}