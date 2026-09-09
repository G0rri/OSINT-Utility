"""Informe de red: ficha completa de un host en una sola consulta.

Reúne las tres consultas rápidas sobre un dominio o IP —registro WHOIS/DNS,
puertos expuestos y cabeceras de seguridad— y las presenta como un informe con
secciones en lugar de tres volcados de consola seguidos.

Se ejecutan en paralelo, no en fila: ninguna depende del resultado de otra (el
escáner de puertos resuelve el nombre por su cuenta), así que el informe tarda
lo que la más lenta y no la suma. Importa porque WHOIS es la más variable: entre
1 y 11 segundos según el TLD.

El escaneo de subdominios queda deliberadamente fuera. Es la única consulta de
la pestaña que se va con frecuencia por encima de los 10 segundos, y meterla
aquí penalizaría cada informe por un dato que no siempre se necesita.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from core.base_module import BaseModule
from modules.port_scanner_module import PortScannerModule
from modules.security_headers_module import SecurityHeadersModule
from modules.whois_dns_module import WhoisDnsModule

logger: logging.Logger = logging.getLogger(__name__)

# Ancho del informe en caracteres. Elegido para llenar la consola sin depender
# del tamaño de la ventana: el informe también se guarda como texto plano.
_ANCHO: int = 70

# Cabecera de seguridad -> (etiqueta corta, para qué sirve si falta).
_CABECERAS: tuple[tuple[str, str], ...] = (
    ("hsts", "HSTS"),
    ("csp", "CSP"),
    ("x_frame", "X-Frame"),
    ("x_content_type", "Sniffing"),
)


def _silencio(_: str) -> None:
    """Descarta la salida de consola de los submódulos.

    El informe se compone a partir de los diccionarios que devuelven, no de lo
    que imprimen; encadenar sus tres salidas sería justo el volcado que este
    módulo intenta evitar.
    """


class NetworkReportModule(BaseModule):
    """Ejecuta WHOIS/DNS, puertos y cabeceras, y compone un informe único."""

    def __init__(self) -> None:
        super().__init__("InformeRed")
        # Instancias propias: así el informe no depende del registro (que a su
        # vez importa los módulos) ni hereda opciones que el usuario haya
        # cambiado en las herramientas sueltas, como desactivar la validación TLS.
        self._whois: WhoisDnsModule = WhoisDnsModule()
        self._puertos: PortScannerModule = PortScannerModule()
        self._cabeceras: SecurityHeadersModule = SecurityHeadersModule()

    def check_health(self) -> tuple[str, str]:
        """El informe está operativo si lo están sus tres componentes."""
        for modulo in (self._whois, self._puertos, self._cabeceras):
            estado, clave = modulo.check_health()
            if estado == "error":
                return "error", clave
        return "ok", "informe_ok"

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        objetivo: str = target.strip()
        callback(f"\n{'=' * _ANCHO}\n")
        callback(f"  INFORME DE RED · {objetivo}\n")
        callback(f"{'=' * _ANCHO}\n\n")
        callback("[*] Consultando registro, puertos y cabeceras en paralelo...\n")

        inicio: float = time.time()
        tareas = {
            "whois": self._cronometrar("Registro", self._whois, objetivo, callback),
            "puertos": self._cronometrar("Puertos", self._puertos, objetivo, callback),
            "cabeceras": self._cronometrar(
                "Cabeceras", self._cabeceras, objetivo, callback
            ),
        }

        resultados_lista = await asyncio.gather(*tareas.values())
        resultados: dict[str, dict[str, Any]] = dict(
            zip(tareas.keys(), resultados_lista, strict=True)
        )
        transcurrido: float = time.time() - inicio

        self._render(objetivo, resultados, transcurrido, callback)

        return {
            "status": "success",
            "target": objetivo,
            "whois": resultados["whois"],
            "puertos": resultados["puertos"],
            "cabeceras": resultados["cabeceras"],
        }

    async def _cronometrar(
        self,
        etiqueta: str,
        modulo: BaseModule,
        objetivo: str,
        callback: Callable[[str], None],
    ) -> dict[str, Any]:
        """Ejecuta un submódulo informando de su avance y aislando su fallo.

        Que una de las tres consultas caiga no debe dejar sin informe a las
        otras dos: la sección afectada se marca como no disponible.
        """
        t0: float = time.time()
        try:
            resultado: dict[str, Any] = await modulo.run(objetivo, _silencio)
        except asyncio.CancelledError:
            raise
        except (RuntimeError, ValueError, OSError) as err:
            logger.error("El informe no pudo completar '%s': %s", etiqueta, err)
            callback(f"    ✗ {etiqueta}: {err}\n")
            return {"status": "error", "error": str(err)}

        callback(f"    ✓ {etiqueta} ({time.time() - t0:.1f} s)\n")
        return resultado if isinstance(resultado, dict) else {"status": "error"}

    # ------------------------------------------------------------------
    # Composición del informe
    # ------------------------------------------------------------------

    def _render(
        self,
        objetivo: str,
        resultados: dict[str, dict[str, Any]],
        transcurrido: float,
        callback: Callable[[str], None],
    ) -> None:
        callback("\n")
        self._seccion_registro(resultados["whois"], callback)
        self._seccion_infraestructura(resultados["puertos"], callback)
        self._seccion_seguridad(resultados["cabeceras"], callback)

        correctas: int = sum(
            1 for r in resultados.values() if r.get("status") == "success"
        )
        callback(f"{'─' * _ANCHO}\n")
        callback(
            f"  Completado en {transcurrido:.1f} s · "
            f"{correctas} de {len(resultados)} consultas correctas\n\n"
        )

    @staticmethod
    def _titulo(texto: str, callback: Callable[[str], None]) -> None:
        callback(f"── {texto} {'─' * max(0, _ANCHO - len(texto) - 4)}\n")

    @staticmethod
    def _campo(etiqueta: str, valor: Any, callback: Callable[[str], None]) -> None:
        callback(f"   {etiqueta:<16} {valor}\n")

    @staticmethod
    def _solo_fecha(valor: Any) -> str:
        """Recorta la hora de una marca temporal WHOIS.

        python-whois devuelve datetime completos ("2007-10-09 18:20:50+00:00");
        en un informe la hora de alta de un dominio es ruido.
        """
        texto: str = str(valor or "?").strip()
        return texto.split(" ")[0] if texto else "?"

    def _no_disponible(
        self, resultado: dict[str, Any], callback: Callable[[str], None]
    ) -> bool:
        """Escribe el motivo si la sección no pudo completarse."""
        if resultado.get("status") == "success":
            return False
        motivo: str = str(resultado.get("error", "no disponible"))
        callback(f"   [!] Sin datos: {motivo}\n\n")
        return True

    def _seccion_registro(
        self, resultado: dict[str, Any], callback: Callable[[str], None]
    ) -> None:
        self._titulo("Registro", callback)
        if self._no_disponible(resultado, callback):
            return

        whois: dict[str, Any] = resultado.get("whois", {}) or {}
        dns: dict[str, Any] = resultado.get("dns", {}) or {}

        if whois:
            self._campo("Registrador", whois.get("registrar", "?"), callback)
            self._campo("Alta", self._solo_fecha(whois.get("creation")), callback)
            self._campo(
                "Caducidad", self._solo_fecha(whois.get("expiration")), callback
            )
        else:
            self._campo("Registrador", "sin datos WHOIS", callback)

        servidores: list[str] = list(whois.get("name_servers", []) or [])
        if servidores:
            resumen: str = servidores[0].lower()
            if len(servidores) > 1:
                resumen += f"  (+{len(servidores) - 1})"
            self._campo("Servidores DNS", resumen, callback)

        registros_mx: list[str] = list(dns.get("MX", []) or [])
        if registros_mx:
            n: int = len(registros_mx)
            self._campo("Correo (MX)", f"{n} registro{'s' if n != 1 else ''}", callback)

        callback("\n")

    def _seccion_infraestructura(
        self, resultado: dict[str, Any], callback: Callable[[str], None]
    ) -> None:
        self._titulo("Infraestructura", callback)
        if self._no_disponible(resultado, callback):
            return

        self._campo("IP", resultado.get("ip", "?"), callback)

        puertos: list[int] = list(resultado.get("ports", []) or [])
        if puertos:
            self._campo("Puertos", ", ".join(str(p) for p in puertos), callback)
        else:
            self._campo("Puertos", "ninguno indexado en Shodan", callback)

        callback("\n")

    def _seccion_seguridad(
        self, resultado: dict[str, Any], callback: Callable[[str], None]
    ) -> None:
        self._titulo("Seguridad web", callback)
        if self._no_disponible(resultado, callback):
            return

        self._campo("Servidor", resultado.get("server", "?"), callback)

        cabeceras: dict[str, Any] = resultado.get("headers", {}) or {}
        faltantes: list[str] = []
        for clave, etiqueta in _CABECERAS:
            valor = cabeceras.get(clave)
            if valor:
                detalle = str(valor)
                corto = detalle if len(detalle) <= 24 else "presente"
                self._campo(etiqueta, f"✔ {corto}", callback)
            else:
                self._campo(etiqueta, "✘ ausente", callback)
                faltantes.append(etiqueta)

        if faltantes:
            callback(
                f"\n   [!] Le faltan {len(faltantes)} protecciones: "
                f"{', '.join(faltantes)}\n"
            )
        else:
            callback("\n   [+] Todas las protecciones comprobadas están puestas.\n")

        callback("\n")
