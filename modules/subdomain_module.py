import asyncio
import httpx
from core.base_module import BaseModule

class SubdomainModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "Subdomain Scanner"
        self.description = "Búsqueda asíncrona de subdominios usando crt.sh"
        
    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando búsqueda de subdominios para: {target}\n")
        
        # Limpiar target en caso de que envíen URLs completas
        target = target.strip().lower()
        if target.startswith("http://") or target.startswith("https://"):
            target = target.split("//")[-1].split("/")[0]

        url = f"https://crt.sh/?q=%.{target}&output=json"
        callback(f"[*] Consultando crt.sh...\n")
        
        subdomains = set()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if isinstance(data, list):
                                for entry in data:
                                    name_value = entry.get("name_value", "")
                                    # name_value puede contener varios dominios separados por saltos de línea
                                    for sub in name_value.splitlines():
                                        sub = sub.strip().lower()
                                        # Filtrar: que no sea vacío, que termine en el target, que no sea idéntico al target
                                        if sub and sub.endswith(target) and sub != target:
                                            # Eliminar comodín si se quiere reportar solo dominios explícitos
                                            if sub.startswith("*."):
                                                sub = sub[2:]
                                            if sub != target:
                                                subdomains.add(sub)
                            else:
                                callback("[-] Error: Formato de respuesta JSON inesperado de crt.sh.\n")
                        except ValueError:
                            callback("[-] Error: JSON corrupto o respuesta no válida recibida de crt.sh.\n")
                    else:
                        callback(f"[-] Error de conexión HTTP. Código de estado: {response.status_code}\n")
                    
                    break # Sale del loop de reintentos
            
            except (httpx.ReadTimeout, httpx.ConnectError) as exc:
                if attempt < max_retries - 1:
                    callback(f"[-] Intento {attempt + 1} fallido por timeout o conexión. Reintentando...\n")
                    await asyncio.sleep(2)
                else:
                    callback(f"[-] Error persistente tras {max_retries} intentos conectando con crt.sh: {exc}\n")
                    return {"status": "error", "error": str(exc)}
            except httpx.RequestError as exc:
                callback(f"[-] Error de red crítico al intentar conectar con crt.sh: {exc}\n")
                return {"status": "error", "error": str(exc)}
            except Exception as e:
                callback(f"[-] Error inesperado en SubdomainModule: {e}\n")
                return {"status": "error", "error": str(e)}

        if subdomains:
            callback(f"\n[+] Se encontraron {len(subdomains)} subdominios únicos:\n")
            # Reportar la lista ordenada a través del callback
            for sub in sorted(list(subdomains)):
                callback(f"    - {sub}\n")
                await asyncio.sleep(0.005) # Para no bloquear la GUI
            
            callback("\n[+] Búsqueda de subdominios finalizada.\n")
            return {"status": "success", "target": target, "subdomains": sorted(list(subdomains))}
        else:
            callback("[-] No se encontraron subdominios.\n")
            return {"status": "success", "target": target, "subdomains": []}
