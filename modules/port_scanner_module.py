import socket
import httpx
import asyncio
from core.base_module import BaseModule

class PortScannerModule(BaseModule):
    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando escaneo de puertos (Shodan InternetDB) para: {target}\n")
        try:
            # La API requiere una IP, así que resolvemos el dominio primero
            ip = await asyncio.to_thread(socket.gethostbyname, target)
            callback(f"[*] Objetivo resuelto a la IP: {ip}\n")
        except Exception:
            callback(f"[-] Error: No se pudo resolver {target} a una IP válida.\n")
            return {"status": "error"}

        url = f"https://internetdb.shodan.io/{ip}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    ports = data.get("ports", [])
                    if ports:
                        callback(f"[+] Puertos abiertos detectados externamente:\n")
                        for p in ports:
                            callback(f"    - Puerto {p} [ABIERTO]\n")
                    else:
                        callback("[-] No se detectaron puertos abiertos en la base de datos de Shodan.\n")
                elif response.status_code == 404:
                    callback("[-] Esta IP no está indexada en Shodan (Probablemente no expone puertos).\n")
                else:
                    callback(f"[-] Error de la API de Shodan: {response.status_code}\n")
            except Exception as e:
                callback(f"[-] Error de red al consultar Shodan: {e}\n")
        
        callback("\n[+] Escaneo finalizado.\n")
        return {"status": "success"}