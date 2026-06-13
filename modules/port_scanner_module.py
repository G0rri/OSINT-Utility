<<<<<<< HEAD
import asyncio
import socket

import httpx

from core.base_module import BaseModule


class PortScannerModule(BaseModule):
    async def run(self, target: str, callback) -> dict:
        callback(
            f"[*] Iniciando escaneo de puertos (Shodan InternetDB) para: {target}\n"
        )
        try:
            # Resolvemos el dominio delegando al pool de hilos
            ip = await asyncio.to_thread(socket.gethostbyname, target)
            callback(f"[*] Objetivo resuelto a la IP: {ip}\n")
        except socket.gaierror:
            callback(
                f"[-] Error de DNS: No se pudo resolver '{target}'. Verifica la ortografía o tu conexión a internet.\n"
            )
            return {"status": "error", "error": "DNS resolution failed"}
        except Exception as e:
            callback(f"[-] Error inesperado al resolver el host: {e}\n")
            return {"status": "error", "error": str(e)}

        url = f"https://internetdb.shodan.io/{ip}"

=======
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
        
>>>>>>> 7724dea621a204eb8ef7157c74d8431613d61dc8
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    ports = data.get("ports", [])
                    if ports:
<<<<<<< HEAD
                        callback("[+] Puertos abiertos detectados externamente:\n")
                        for p in ports:
                            callback(f"    - Puerto {p} [ABIERTO]\n")
                    else:
                        callback(
                            "[-] No se detectaron puertos abiertos en la base de datos de Shodan.\n"
                        )
                elif response.status_code == 404:
                    callback(
                        "[-] Esta IP no está indexada en Shodan (Probablemente no expone puertos).\n"
                    )
=======
                        callback(f"[+] Puertos abiertos detectados externamente:\n")
                        for p in ports:
                            callback(f"    - Puerto {p} [ABIERTO]\n")
                    else:
                        callback("[-] No se detectaron puertos abiertos en la base de datos de Shodan.\n")
                elif response.status_code == 404:
                    callback("[-] Esta IP no está indexada en Shodan (Probablemente no expone puertos).\n")
>>>>>>> 7724dea621a204eb8ef7157c74d8431613d61dc8
                else:
                    callback(f"[-] Error de la API de Shodan: {response.status_code}\n")
            except Exception as e:
                callback(f"[-] Error de red al consultar Shodan: {e}\n")
<<<<<<< HEAD

        callback("\n[+] Escaneo finalizado.\n")
        return {"status": "success"}
=======
        
        callback("\n[+] Escaneo finalizado.\n")
        return {"status": "success"}
>>>>>>> 7724dea621a204eb8ef7157c74d8431613d61dc8
