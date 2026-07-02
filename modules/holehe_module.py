import os
import sys
import re
import logging
import asyncio
import httpx
from typing import Any, Callable
from core.base_module import BaseModule

# Configuración del logger nativo del módulo para entornos de producción
logger: logging.Logger = logging.getLogger("OSINTApp.HoleheModule")

# Silenciamos los loggers internos de las librerías de red para mantener la consola limpia
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

class HoleheModule(BaseModule):
    """Módulo profesional optimizado para el rastreo, limpieza y enriquecimiento libre de emails."""

    def __init__(self, name: str = "Holehe") -> None:
        super().__init__(name)

    def check_health(self) -> tuple[str, str]:
        """Comprueba de forma síncrona si el entorno de Holehe está operativo."""
        try:
            import holehe  # noqa: F401
            return "ok", "Módulo Holehe cargado correctamente en el entorno virtual."
        except ImportError:
            logger.error("La librería 'holehe' no está instalada en el entorno virtual actual.")
            return "error", "Librería 'holehe' ausente en requirements.txt."

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Ejecuta el rastreo de email eliminando el ruido visual de banners de forma multiplataforma."""
        logger.info(f"Iniciando ciclo de inteligencia OSINT autónomo para: {target}")
        
        resultados_finales: dict[str, Any] = {
            "email": target,
            "sitios_detectados": [],
            "brechas_seguridad": {},
            "identidad_google": {}
        }

        callback(f"[★] Análisis avanzado para: {target}\n")
        callback("-" * 60 + "\n")

        ansi_regex: re.Pattern[str] = re.compile(r'\x1b\[[0-9;]*m')
        
        inline_script: str = (
            "import sys; "
            "from holehe.core import main; "
            "sys.argv = ['holehe', sys.argv[1], '--only-used']; "
            "main()"
        )
        
        comando: list[str] = [sys.executable, "-c", inline_script, target]
        logger.debug(f"Lanzando comando de subproceso unificado: {' '.join(comando)}")

        try:
            env_limpio = os.environ.copy()
            env_limpio["PYTHONUNBUFFERED"] = "1"

            procesos_async = await asyncio.create_subprocess_exec(
                *comando,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env_limpio,
                shell=False
            )

            # Lector de salida estándar (Captura de aciertos positivos limpios)
            async def leer_stdout() -> None:
                if procesos_async.stdout:
                    while True:
                        linea_bytes = await procesos_async.stdout.readline()
                        if not linea_bytes:
                            break
                        linea_texto = ansi_regex.sub('', linea_bytes.decode("utf-8", errors="ignore")).strip()
                        
                        # Filtros quirúrgicos anti-spam institucionales
                        if any(ruido in linea_texto for ruido in [
                            "Twitter :", "Github :", "For BTC Donations", 
                            "websites checked in", "Búsqueda en Holehe", "TASK"
                        ]):
                            continue
                        if "%|" in linea_texto or "[!]" in linea_texto or "REPLACEMENT CHARACTER" in linea_texto:
                            continue
                        if not linea_texto or linea_texto.startswith("****"):
                            continue
                            
                        if "[+]" in linea_texto:
                            # Exclusión de la leyenda de Holehe que se colaba al final
                            if any(w in linea_texto.lower() for w in ["email used", "rate limit", "not used", "legend"]):
                                continue
                                
                            sitio = linea_texto.replace("[+]", "").strip()
                            if sitio and not sitio.startswith(":") and len(sitio) > 1:
                                resultados_finales["sitios_detectados"].append(sitio)
                                callback(f"  [+] Registrado en: {sitio}\n")

            # Lector de errores silenciado (Evita las alertas rojas en la UI)
            async def leer_stderr() -> None:
                if procesos_async.stderr:
                    while True:
                        linea_bytes = await procesos_async.stderr.readline()
                        if not linea_bytes:
                            break
                        linea_texto = linea_bytes.decode("utf-8", errors="ignore").strip()
                        if linea_texto:
                            logger.debug(f"Traza secundaria de Holehe: {linea_texto}")

            await asyncio.gather(leer_stdout(), leer_stderr())
            await procesos_async.wait()

        except OSError as exc:
            logger.error(f"Fallo crítico de llamada del sistema al invocar subproceso: {exc}")
            callback("[⚠️] Error interno al procesar el motor de firmas local.\n")
        except asyncio.CancelledError:
            logger.warning("La tarea asíncrona de Holehe fue abortada de forma externa.")
            raise

        if not resultados_finales["sitios_detectados"]:
            callback("  ℹ️ No se detectaron registros activos en los módulos estándar.\n")

        # 2. ENRIQUECIMIENTO MEDIANTE FUGAS DE DATOS (XposedOrNot)
        await self._analizar_brechas_libre(target, callback, resultados_finales)

        # 3. EXTRACCIÓN PASIVA DE INTELIGENCIA DE GOOGLE SUITE
        if target.lower().endswith("@gmail.com"):
            await self._analizar_perfil_google(target, callback, resultados_finales)

        return resultados_finales

    async def _analizar_brechas_libre(self, email: str, callback: Callable[[str], None], resultados: dict[str, Any]) -> None:
        """Consulta asíncronamente el endpoint público y libre de XposedOrNot."""
        callback("\n[🔍] Consultando inteligencia de brechas de datos (XposedOrNot)...\n")
        
        # CORRECCIÓN VITAL: Endpoint oficial que no requiere API Keys ni sufre bloqueos
        url_xposed: str = f"https://api.xposedornot.com/v1/check-email/{email}"
        headers: dict[str, str] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(url_xposed, headers=headers, timeout=12.0)
                
                if response.status_code == 200:
                    payload = response.json()
                    breaches_array = payload.get("breaches", [])
                    
                    # Desempaquetamos la lista doble que devuelve XposedOrNot [["brecha1", "brecha2"]]
                    brechas = breaches_array[0] if breaches_array and isinstance(breaches_array[0], list) else breaches_array
                    
                    if brechas:
                        resultados["brechas_seguridad"] = brechas
                        callback(f"  ⚠️ ¡Alerta! El correo se localizó en {len(brechas)} filtraciones de datos públicas.\n")
                        for breach in brechas[:3]:
                            callback(f"    - Exposición confirmada en: {breach}\n")
                    else:
                        callback("  ✅ Correo limpio en repositorios históricos de filtraciones.\n")
                        
                elif response.status_code == 404:
                    callback("  ✅ No se han detectado exposiciones en fuentes de datos indexadas.\n")
                elif response.status_code == 429:
                    callback("  [×] Límite de consultas gratuitas alcanzado. Inténtalo más tarde.\n")
                else:
                    logger.warning(f"El servidor de XposedOrNot respondió con código: {response.status_code}")
                    callback("  [×] Repositorio de consultas temporalmente fuera de línea.\n")
            except (httpx.RequestError, ValueError) as exc:
                logger.error(f"Fallo de conectividad o parseo con servidor OSINT: {exc}")
                callback("  [×] Error de red al conectar con el servidor libre de credenciales.\n")

    async def _analizar_perfil_google(self, email: str, callback: Callable[[str], None], resultados: dict[str, Any]) -> None:
        """Valida pasivamente la existencia de la cuenta interrogando el servidor de avatares de Google."""
        callback("\n[👤] Analizando vectores de identidad activa en Google Suite...\n")
        url_google: str = f"https://profiles.google.com/s/v/p/il/{email}/profile.jpg"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                response = await client.get(url_google, headers=headers, timeout=8.0)
                
                if response.status_code == 200:
                    resultados["identidad_google"] = {"cuenta_activa": True, "avatar_url": str(response.url)}
                    callback("  ⚡ Cuenta de Google verificada como: ACTIVA (Existe cuenta vinculada)\n")
                    if "default_avatar" not in str(response.url):
                        callback(f"  🔗 URL del Avatar Público: {response.url}\n")
                elif response.status_code == 404:
                    callback("  ℹ️ Perfil Oculto: La cuenta existe pero no posee un avatar público configurable.\n")
                else:
                    callback("  ℹ️ No se pudo comprobar el estado de privacidad en los servidores de Google.\n")
            except httpx.RequestError as exc:
                logger.error(f"Error de transporte HTTP al consultar endpoints de Google: {exc}")
                callback("  [×] Imposible conectar con los servidores de validación de Google.\n")