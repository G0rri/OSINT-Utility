"""Rastreo de correos mediante la API Python de Holehe.

Hasta ahora este módulo lanzaba `holehe` como subproceso y reconstruía los
resultados filtrando su salida de consola con una lista de cadenas mágicas
("For BTC Donations", "websites checked in"…). Ese acoplamiento al formato de
impresión de una herramienta de terceros se rompía en silencio con cada cambio
de versión y descartaba información que Holehe sí produce.

Ahora se invocan directamente las corrutinas de `holehe.modules`, que devuelven
un diccionario estructurado por sitio. Además de ser estable frente a cambios de
formato, esto expone el correo y el teléfono de recuperación que el parseo de
texto perdía.
"""

import asyncio
import logging
from collections.abc import Callable, Sequence
from typing import Any

import httpx

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger("OSINTApp.HoleheModule")

# Silenciamos los loggers internos de las librerías de terceros para no inundar
# la consola de la GUI. BeautifulSoup avisa por logging (no por print) cada vez
# que un sitio devuelve HTML mal codificado, algo habitual al consultar ~120
# servicios: sin esto, la consola se llena de avisos ajenos al análisis.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("bs4").setLevel(logging.ERROR)
logging.getLogger("bs4.dammit").setLevel(logging.ERROR)

# Holehe lanza sus ~120 comprobaciones de golpe. Limitamos la concurrencia para
# no disparar los límites de tasa de los sitios ni saturar la red del usuario.
_MAX_CONCURRENCY: int = 30
_REQUEST_TIMEOUT: float = 10.0
_PROGRESS_EVERY: int = 25

# Caché de las corrutinas descubiertas: el escaneo de paquetes solo se hace una vez.
_WEBSITE_FUNCTIONS: list[Callable[..., Any]] | None = None


def _discover_websites() -> list[Callable[..., Any]]:
    """Descubre las corrutinas de comprobación que expone Holehe.

    `import_submodules` recorre `holehe.modules` e importa cada submódulo, por lo
    que solo se ejecuta la primera vez y se cachea.
    """
    global _WEBSITE_FUNCTIONS
    if _WEBSITE_FUNCTIONS is None:
        from holehe.core import get_functions, import_submodules

        _WEBSITE_FUNCTIONS = list(get_functions(import_submodules("holehe.modules")))
        logger.info("Holehe: %d comprobaciones disponibles.", len(_WEBSITE_FUNCTIONS))
    return _WEBSITE_FUNCTIONS


class HoleheModule(BaseModule):
    """Rastrea en qué servicios está registrado un correo electrónico."""

    def __init__(self, name: str = "Holehe") -> None:
        super().__init__(name)

    def check_health(self) -> tuple[str, str]:
        """Comprueba que la librería Holehe esté instalada y exponga su API."""
        try:
            from holehe.core import get_functions, import_submodules  # noqa: F401
        except ImportError as err:
            logger.error("La librería 'holehe' no está disponible: %s", err)
            return "error", "holehe_missing"
        return "ok", "holehe_ok"

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Consulta todos los sitios soportados y enriquece con fuentes externas."""
        logger.info("Iniciando rastreo de Holehe para: %s", target)

        resultados: dict[str, Any] = {
            "email": target,
            "sitios_detectados": [],
            "detalles": [],
            "limitados": [],
            "brechas_seguridad": {},
            "identidad_google": {},
        }

        callback(f"[★] Análisis avanzado para: {target}\n")
        callback("-" * 60 + "\n")

        if not self._is_email(target):
            callback(f"[-] '{target}' no tiene forma de dirección de correo.\n")
            resultados["status"] = "error"
            resultados["error"] = "invalid_email"
            return resultados

        await self._rastrear_sitios(target, callback, resultados)

        # Enriquecimiento con fuentes que Holehe no cubre.
        await self._analizar_brechas_libre(target, callback, resultados)
        if target.lower().endswith("@gmail.com"):
            await self._analizar_perfil_google(target, callback, resultados)

        resultados["status"] = "success"
        return resultados

    @staticmethod
    def _is_email(value: str) -> bool:
        """Valida la dirección con la misma comprobación que usa Holehe."""
        try:
            from holehe.core import is_email

            return bool(is_email(value))
        except ImportError:
            return "@" in value and "." in value.split("@")[-1]

    async def _rastrear_sitios(
        self,
        email: str,
        callback: Callable[[str], None],
        resultados: dict[str, Any],
    ) -> None:
        """Ejecuta las comprobaciones de Holehe y reporta los aciertos al vuelo."""
        try:
            websites: Sequence[Callable[..., Any]] = await asyncio.to_thread(
                _discover_websites
            )
        except ImportError as err:
            logger.error("No se pudo cargar el catálogo de Holehe: %s", err)
            callback("[-] La librería Holehe no está disponible en este entorno.\n")
            return

        total: int = len(websites)
        callback(f"[*] Consultando {total} servicios...\n")

        salida: list[dict[str, Any]] = []
        completadas: int = 0
        semaforo: asyncio.Semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:

            async def _ejecutar(funcion: Callable[..., Any]) -> None:
                nonlocal completadas
                async with semaforo:
                    await self._invocar_comprobacion(funcion, email, client, salida)
                completadas += 1
                if completadas % _PROGRESS_EVERY == 0:
                    callback(f"    ... {completadas}/{total} comprobados\n")

            await asyncio.gather(*(_ejecutar(f) for f in websites))

        self._volcar_resultados(salida, callback, resultados)

    @staticmethod
    async def _invocar_comprobacion(
        funcion: Callable[..., Any],
        email: str,
        client: httpx.AsyncClient,
        salida: list[dict[str, Any]],
    ) -> None:
        """Ejecuta una comprobación aislando sus fallos del resto del escaneo.

        Este es el único punto del proyecto donde se captura `Exception` de forma
        genérica, y es deliberado: son ~120 módulos de terceros que parsean HTML
        ajeno y pueden lanzar prácticamente cualquier cosa (IndexError al trocear
        una respuesta inesperada, KeyError, errores de codificación…). Dejar
        escapar una de ellas abortaría las 119 restantes. `asyncio.CancelledError`
        hereda de `BaseException`, así que la cancelación del usuario sigue
        propagándose sin quedar atrapada aquí.
        """
        nombre: str = getattr(funcion, "__name__", "desconocido")
        try:
            await funcion(email, client, salida)
        except Exception as err:  # noqa: BLE001
            logger.debug("La comprobación '%s' falló y se omite: %s", nombre, err)

    @staticmethod
    def _volcar_resultados(
        salida: list[dict[str, Any]],
        callback: Callable[[str], None],
        resultados: dict[str, Any],
    ) -> None:
        """Ordena, reporta y acumula los hallazgos del escaneo."""
        encontrados: list[dict[str, Any]] = sorted(
            (r for r in salida if r.get("exists")),
            key=lambda r: str(r.get("name", "")),
        )
        limitados: list[str] = sorted(
            str(r.get("name", "")) for r in salida if r.get("rateLimit")
        )

        resultados["limitados"] = limitados

        if not encontrados:
            callback(
                "\n  ℹ️ No se detectaron registros activos en los servicios consultados.\n"
            )
        else:
            callback(f"\n[+] Registrado en {len(encontrados)} servicios:\n")

        for registro in encontrados:
            dominio: str = str(registro.get("domain") or registro.get("name", ""))
            resultados["sitios_detectados"].append(dominio)
            resultados["detalles"].append(registro)
            callback(f"  [+] Registrado en: {dominio}\n")

            # Información que el parseo de la salida de consola descartaba.
            recuperacion: Any = registro.get("emailrecovery")
            telefono: Any = registro.get("phoneNumber")
            if recuperacion:
                callback(f"        ↳ Correo de recuperación: {recuperacion}\n")
            if telefono:
                callback(f"        ↳ Teléfono de recuperación: {telefono}\n")

        if limitados:
            callback(
                f"\n  [×] {len(limitados)} servicios no respondieron por límite "
                "de tasa; sus resultados son indeterminados.\n"
            )

    # ------------------------------------------------------------------
    # Enriquecimiento externo
    # ------------------------------------------------------------------

    async def _analizar_brechas_libre(
        self, email: str, callback: Callable[[str], None], resultados: dict[str, Any]
    ) -> None:
        """Consulta el endpoint público y libre de XposedOrNot."""
        callback(
            "\n[🔍] Consultando inteligencia de brechas de datos (XposedOrNot)...\n"
        )

        url_xposed: str = f"https://api.xposedornot.com/v1/check-email/{email}"
        headers: dict[str, str] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(url_xposed, headers=headers, timeout=12.0)

                if response.status_code == 200:
                    payload = response.json()
                    breaches_array = payload.get("breaches", [])

                    # XposedOrNot anida el listado: [["brecha1", "brecha2"]]
                    brechas = (
                        breaches_array[0]
                        if breaches_array and isinstance(breaches_array[0], list)
                        else breaches_array
                    )

                    if brechas:
                        resultados["brechas_seguridad"] = brechas
                        callback(
                            f"  ⚠️ ¡Alerta! El correo se localizó en {len(brechas)} "
                            "filtraciones de datos públicas.\n"
                        )
                        for breach in brechas[:3]:
                            callback(f"    - Exposición confirmada en: {breach}\n")
                    else:
                        callback(
                            "  ✅ Correo limpio en repositorios históricos de filtraciones.\n"
                        )

                elif response.status_code == 404:
                    callback(
                        "  ✅ No se han detectado exposiciones en fuentes de datos indexadas.\n"
                    )
                elif response.status_code == 429:
                    callback(
                        "  [×] Límite de consultas gratuitas alcanzado. Inténtalo más tarde.\n"
                    )
                else:
                    logger.warning(
                        "XposedOrNot respondió con código: %s", response.status_code
                    )
                    callback(
                        "  [×] Repositorio de consultas temporalmente fuera de línea.\n"
                    )
            except (httpx.RequestError, ValueError) as exc:
                logger.error("Fallo de conectividad o parseo con XposedOrNot: %s", exc)
                callback(
                    "  [×] Error de red al conectar con el servidor libre de credenciales.\n"
                )

    async def _analizar_perfil_google(
        self, email: str, callback: Callable[[str], None], resultados: dict[str, Any]
    ) -> None:
        """Valida pasivamente la cuenta interrogando el servidor de avatares de Google."""
        callback("\n[👤] Analizando vectores de identidad activa en Google Suite...\n")
        url_google: str = f"https://profiles.google.com/s/v/p/il/{email}/profile.jpg"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                response = await client.get(url_google, headers=headers, timeout=8.0)

                if response.status_code == 200:
                    resultados["identidad_google"] = {
                        "cuenta_activa": True,
                        "avatar_url": str(response.url),
                    }
                    callback(
                        "  ⚡ Cuenta de Google verificada como: ACTIVA (Existe cuenta vinculada)\n"
                    )
                    if "default_avatar" not in str(response.url):
                        callback(f"  🔗 URL del Avatar Público: {response.url}\n")
                elif response.status_code == 404:
                    callback(
                        "  ℹ️ Perfil Oculto: La cuenta existe pero no posee un avatar público configurable.\n"
                    )
                else:
                    callback(
                        "  ℹ️ No se pudo comprobar el estado de privacidad en los servidores de Google.\n"
                    )
            except httpx.RequestError as exc:
                logger.error("Error HTTP al consultar endpoints de Google: %s", exc)
                callback(
                    "  [×] Imposible conectar con los servidores de validación de Google.\n"
                )
