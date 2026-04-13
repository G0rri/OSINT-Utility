import httpx
import asyncio
from core.base_module import BaseModule

class WaybackModule(BaseModule):
    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Consultando Wayback Machine (CDX API) para: {target}\n")
        
        # Atacamos a la base de datos profunda pidiendo solo 1 resultado
        url = f"http://web.archive.org/cdx/search/cdx?url={target}&output=json&limit=1&fl=timestamp,original"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    # El índice 0 son los títulos de las columnas, el 1 son los datos
                    if len(data) > 1:
                        timestamp = data[1][0]
                        original_url = data[1][1]
                        
                        # Formateamos YYYYMMDDhhmmss a YYYY-MM-DD
                        formatted_date = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
                        snapshot_url = f"https://web.archive.org/web/{timestamp}/{original_url}"
                        
                        callback(f"[+] ¡Captura histórica encontrada!\n")
                        callback(f"    - Fecha del registro más antiguo: {formatted_date}\n")
                        callback(f"    - Enlace al archivo: {snapshot_url}\n")
                    else:
                        callback("[-] No se encontraron capturas históricas para este objetivo.\n")
                else:
                    callback(f"[-] Error devuelto por Archive.org: Código {response.status_code}\n")
            except Exception as e:
                callback(f"[-] Error de red crítico: {str(e)}\n")
                
        callback("\n[+] Consulta finalizada.\n")
        return {"status": "success"}