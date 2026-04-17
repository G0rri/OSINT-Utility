import asyncio
import httpx
import re
import os
from core.base_module import BaseModule

class VirustotalModule(BaseModule):
    """
    Módulo nativo asíncrono para consultar la API v3 de VirusTotal.
    Detecta automáticamente si el objetivo es una IP o un dominio.
    """
    def __init__(self):
        super().__init__()
        # Lee la API Key desde el entorno (carga desde el archivo .env)
        self.api_key = os.getenv("VIRUSTOTAL_API_KEY")

    async def run(self, target: str, callback) -> dict:
        if not self.api_key or self.api_key == "TU_API_KEY_AQUI":
            callback("[-] Error crítico: No se encontró VIRUSTOTAL_API_KEY en el archivo .env\n")
            return {"status": "error", "error": "Missing API Key"}

        callback(f"[*] Iniciando análisis en VirusTotal para: {target}\n")

        # Regex para comprobar si el objetivo es IP o Dominio
        is_ip = re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target)
        endpoint = f"ip_addresses/{target}" if is_ip else f"domains/{target}"
        url = f"https://www.virustotal.com/api/v3/{endpoint}"

        headers = {
            "accept": "application/json",
            "x-apikey": self.api_key
        }

        try:
            # Petición asíncrona usando httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                
                # Obtenemos al dueño en caso de que sea una IP
                owner = data.get('data', {}).get('attributes', {}).get('as_owner', 'Desconocido') if is_ip else "N/A"

                # Enviamos los resultados a la GUI
                callback("[+] Resultados obtenidos de los motores de análisis:\n")
                callback(f"    - 🔴 Malicioso:   {stats.get('malicious', 0)}\n")
                callback(f"    - 🟠 Sospechoso:  {stats.get('suspicious', 0)}\n")
                callback(f"    - 🟢 Inofensivo:  {stats.get('harmless', 0)}\n")
                callback(f"    - ⚪ Indetectado: {stats.get('undetected', 0)}\n")
                
                if is_ip:
                    callback(f"    - 🏢 Propietario (ASN): {owner}\n")
                    
                callback("\n[+] Búsqueda en VirusTotal finalizada.\n")
                return {"status": "success", "target": target, "stats": stats}

            # Manejo de Códigos de Error HTTP comunes
            elif response.status_code == 401:
                callback("[-] Error 401: Tu API Key es inválida, falta o ha caducado.\n")
            elif response.status_code == 404:
                callback("[-] Error 404: Este objetivo nunca ha sido escaneado en VirusTotal.\n")
            elif response.status_code == 429:
                callback("[-] Error 429: Has superado el límite de peticiones gratuitas por minuto.\n")
            else:
                callback(f"[-] Error de API inesperado: Código HTTP {response.status_code}\n")
                
            return {"status": "error", "error": f"HTTP {response.status_code}"}

        except Exception as e:
            callback(f"[-] Error de red crítico al contactar VirusTotal: {str(e)}\n")
            return {"status": "error", "error": str(e)}