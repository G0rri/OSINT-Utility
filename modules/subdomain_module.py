import asyncio
from urllib.parse import urlparse

import httpx

from core.base_module import BaseModule
from core.visualizer import NetworkVisualizer


class SubdomainModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "Subdomain Scanner"
        self.description = (
            "Búsqueda asíncrona de subdominios usando crt.sh y HackerTarget"
        )

    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Iniciando búsqueda de subdominios para: {target}\n")

        # Limpieza a prueba de balas usando la librería estándar
        target = target.strip().lower()
        if "://" in target:
            target = urlparse(target).netloc or target
        else:
            # Por si introducen algo como "target.com/ruta" sin el esquema http
            target = urlparse(f"http://{target}").netloc or target

        # Eliminar el puerto si el usuario lo incluyó (ej: target.com:8080)
        target = target.split(":")[0]

        subdomains = set()

        async with httpx.AsyncClient(timeout=25.0) as client:
            # --- Fuente 1: crt.sh ---
            callback("[*] Consultando crt.sh...\n")
            crtsh_url = f"https://crt.sh/?q=%.{target}&output=json"
            try:
                response = await client.get(crtsh_url)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for entry in data:
                            for sub in entry.get("name_value", "").splitlines():
                                sub = sub.strip().lower()
                                if sub.startswith("*."):
                                    sub = sub[2:]
                                # Filtrar: sin @, que termine en target y no sea idéntico
                                if (
                                    sub
                                    and "@" not in sub
                                    and (sub.endswith(f".{target}") or sub == target)
                                ):
                                    if sub != target:
                                        subdomains.add(sub)
                        callback(
                            f"[+] crt.sh: {len(subdomains)} subdominios encontrados.\n"
                        )
                    else:
                        callback("[-] crt.sh: Respuesta inesperada.\n")
                else:
                    callback(
                        f"[-] crt.sh: Error HTTP {response.status_code}. Continuando con siguiente fuente...\n"
                    )
            except Exception as e:
                callback(f"[-] crt.sh: Error de conexión ({e}). Continuando...\n")

            # --- Fuente 2: HackerTarget ---
            callback("[*] Consultando HackerTarget...\n")
            ht_url = f"https://api.hackertarget.com/hostsearch/?q={target}"
            try:
                response = await client.get(ht_url, timeout=20.0)
                if (
                    response.status_code == 200
                    and "error" not in response.text.lower()[:50]
                ):
                    count_before = len(subdomains)
                    for line in response.text.splitlines():
                        parts = line.split(",")
                        if parts:
                            sub = parts[0].strip().lower()
                            if sub and "@" not in sub and sub.endswith(f".{target}"):
                                subdomains.add(sub)
                    new_found = len(subdomains) - count_before
                    callback(
                        f"[+] HackerTarget: {new_found} subdominios adicionales encontrados.\n"
                    )
                else:
                    callback(
                        "[-] HackerTarget: Sin resultados o límite de API alcanzado.\n"
                    )
            except Exception as e:
                callback(f"[-] HackerTarget: Error de conexión ({e}).\n")

        if subdomains:
            sorted_subs = sorted(list(subdomains))
            callback(
                f"\n[+] Total: {len(sorted_subs)} subdominios únicos encontrados:\n"
            )
            for sub in sorted_subs:
                callback(f"    - {sub}\n")
                await asyncio.sleep(0.005)

            # --- Generar Grafo ---
            callback("\n[*] Generando grafo interactivo de red...\n")
            try:
                graph_path = NetworkVisualizer.generate_subdomain_graph(
                    target, sorted_subs
                )
                NetworkVisualizer.open_in_browser(graph_path)
                callback("[+] Grafo abierto en el navegador predeterminado.\n")
                callback(f"    (Archivo temporal: {graph_path})\n")
            except Exception as e:
                callback(f"[-] Error al generar/abrir el grafo: {e}\n")

            callback("\n[+] Búsqueda de subdominios finalizada.\n")
            return {"status": "success", "target": target, "subdomains": sorted_subs}
        else:
            callback("[-] No se encontraron subdominios en ninguna fuente.\n")
            return {"status": "success", "target": target, "subdomains": []}
