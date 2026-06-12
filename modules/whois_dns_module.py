import asyncio
import whois
import dns.asyncresolver
import dns.resolver
from core.base_module import BaseModule

class WhoisDnsModule(BaseModule):
    """
    Módulo nativo asíncrono para información WHOIS y resolución de registros DNS locales.
    """
    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando recolección WHOIS y DNS para el dominio: {target}\n")
        
        results = {"target": target, "whois": {}, "dns": {}}

        # ----- 1. SECCIÓN WHOIS -----
        callback("[*] Consultando información WHOIS...\n")
        try:
            # whois.whois es una llamada de red bloqueante nativa al socket port 43.
            # Según tu regla de cero congelaciones, lo delegamos al pool de threads interno de asyncio
            # usando to_thread() para preservar la fluidez de tkinter.
            w = await asyncio.to_thread(whois.whois, target)
            
            if not w.domain_name:
                callback("[-] WHOIS: No se encontró información registrada o el dominio está disponible.\n")
            else:
                registrar = w.registrar or "Desconocido"
                creation = w.creation_date
                expiration = w.expiration_date
                
                # Desempaquetar listas si WHOIS devuelve multiples fechas
                if isinstance(creation, list): creation = creation[0]
                if isinstance(expiration, list): expiration = expiration[0]
                
                name_servers = w.name_servers or []
                if isinstance(name_servers, str): name_servers = [name_servers]
                
                callback("[+] Resultados WHOIS:\n")
                callback(f"    - 🏢 Registrador: {registrar}\n")
                callback(f"    - 📅 Creación:    {creation}\n")
                callback(f"    - ⏰ Expiración:  {expiration}\n")
                
                if name_servers:
                    callback("    - 🌐 Name Servers:\n")
                    for ns in name_servers:
                        callback(f"       • {ns}\n")
                
                results["whois"] = {
                    "registrar": registrar,
                    "creation": str(creation),
                    "expiration": str(expiration),
                    "name_servers": name_servers
                }
        except Exception as e:
            callback(f"[-] Error al consultar el servidor WHOIS: {e}\n")


        # ----- 2. SECCIÓN DNS -----
        callback("\n[*] Resolviendo registros DNS...\n")
        
        # dnspython tiene un resolver asíncrono nativo
        resolver = dns.asyncresolver.Resolver()
        
        records_to_check = ['A', 'MX', 'TXT']
        for record_type in records_to_check:
            try:
                # Resolvemos verdaderamente asíncrono gracias a asyncresolver
                answers = await resolver.resolve(target, record_type)
                
                callback(f"[+] Registros {record_type}:\n")
                record_list = []
                for rdata in answers:
                    text_rdata = rdata.to_text()
                    callback(f"    - {text_rdata}\n")
                    record_list.append(text_rdata)
                    
                results["dns"][record_type] = record_list
                
            except dns.resolver.NoAnswer:
                callback(f"[-] Registros {record_type}: No se encontraron respuestas para este tipo.\n")
            except dns.resolver.NXDOMAIN:
                callback(f"[-] Error: El dominio introducido no existe (NXDOMAIN).\n")
                break  # Detenemos consultas de este dominio si ya falló su existencia primaria
            except dns.resolver.NoNameservers:
                callback(f"[-] Error: Los Servidores DNS no respondieron o están fallando profundamente.\n")
                break
            except Exception as e:
                callback(f"[-] Error inesperado al resolver la entrada {record_type}: {e}\n")
                
            # Yield preventivo luego de cada consulta para que corran animaciones en main.py y se vea suave
            await asyncio.sleep(0.01)
                
        callback("\n[+] Análisis local de WHOIS y DNS finalizado.\n")
        results["status"] = "success"
        
        return results
