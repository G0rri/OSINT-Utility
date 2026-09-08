"""Punto de entrada de OSINT-Utility V2.

Arranca el entorno, crea la ventana principal y mantiene vivos a la vez el
bucle de eventos de asyncio y el de Tkinter.
"""

import asyncio
import logging
import tkinter as tk
from typing import Any

import customtkinter as ctk

from core.config import bootstrap_environment
from ui.app import OSINTApp

# Intervalo de refresco de la GUI dentro del bucle de asyncio.
_UI_TICK_SECONDS: float = 0.02


def _report_tk_exception(exc: Any, val: Any, tb: Any) -> None:
    """Registra las excepciones internas de Tk en lugar de descartarlas.

    Silenciarlas hacía invisibles fallos reales de la interfaz.
    """
    logging.getLogger("OSINTApp.GUI").error(
        "Excepción no controlada en el bucle de Tkinter: %s: %s",
        getattr(exc, "__name__", exc),
        val,
    )


async def tkinter_async_loop() -> None:
    """Cede el control alternativamente a Tkinter y al bucle de asyncio."""
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    app: OSINTApp = OSINTApp(loop)
    app.report_callback_exception = _report_tk_exception

    while app.is_running:
        try:
            app.update()
        except tk.TclError:
            break
        await asyncio.sleep(_UI_TICK_SECONDS)


def main() -> None:
    bootstrap_environment()

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    asyncio.run(tkinter_async_loop())


if __name__ == "__main__":
    main()
