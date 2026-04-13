import httpx
from core.base_module import BaseModule

class SecurityHeadersModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "Security Headers Analyzer"
        self.description = "Analiza y verifica las cabeceras HTTP de seguridad de un servidor"

    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando análisis de cabeceras de seguridad para: {target}\n")
        
        target = target.strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            target = f"https://{target}"
            
        callback(f"[*] Evaluando cabeceras en: {target}\n")
        
        headers_req = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        
        response = None
        
        try:
            # Deshabilitamos verify=False solo a nivel de módulo para ignorar errores SSL y llegar a las cabeceras
            async with httpx.AsyncClient(verify=False) as client:
                try:
                    response = await client.head(target, headers=headers_req, follow_redirects=True, timeout=10.0)
                except httpx.RequestError:
                    callback("[*] Petición HEAD falló, reintentando con GET...\n")
                    response = await client.get(target, headers=headers_req, follow_redirects=True, timeout=10.0)
                    
                if response:
                    callback(f"[+] Conexión exitosa, procesando respuesta HTTP {response.status_code}...\n\n")
                    
                    server = response.headers.get("Server", "Oculto/Desconocido")
                    hsts = response.headers.get("Strict-Transport-Security")
                    csp = response.headers.get("Content-Security-Policy")
                    x_frame = response.headers.get("X-Frame-Options")
                    x_content_type = response.headers.get("X-Content-Type-Options")
                    
                    callback(f"[*] Software del Servidor detectado: {server}\n\n")
                    
                    if hsts:
                        callback(f"    [+] Strict-Transport-Security (HSTS): Presente\n")
                    else:
                        callback(f"    [!] Strict-Transport-Security (HSTS): Faltante (Vulnerable)\n")
                        
                    if csp:
                        callback(f"    [+] Content-Security-Policy (CSP): Presente\n")
                    else:
                        callback(f"    [!] Content-Security-Policy (CSP): Faltante (Vulnerable)\n")
                        
                    if x_frame:
                        callback(f"    [+] X-Frame-Options (Clickjacking): Presente [{x_frame}]\n")
                    else:
                        callback(f"    [!] X-Frame-Options (Clickjacking): Faltante (Vulnerable)\n")
                        
                    if x_content_type:
                        callback(f"    [+] X-Content-Type-Options (Sniffing): Presente [{x_content_type}]\n")
                    else:
                        callback(f"    [!] X-Content-Type-Options (Sniffing): Faltante (Vulnerable)\n")
                        
                    callback("\n[+] Análisis de cabeceras de seguridad finalizado.\n")
                    return {"status": "success", "target": target}
                    
        except httpx.RequestError as exc:
            callback(f"[-] Error de red al intentar conectar con el servidor: {exc}\n")
            return {"status": "error", "error": str(exc)}
        except Exception as e:
            callback(f"[-] Error inesperado en SecurityHeadersModule: {e}\n")
            return {"status": "error", "error": str(e)}

        return {"status": "error"}
