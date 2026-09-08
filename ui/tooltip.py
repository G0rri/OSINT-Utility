"""ToolTip flotante para los componentes de la interfaz.

Admite un titular destacado sobre el cuerpo: en los tooltips de ayuda el titular
dice qué obtienes con la herramienta, que es lo que se lee de un vistazo.
"""

import tkinter as tk
from typing import Any

_DELAY_MS: int = 500
# Ancho de envoltura. Los cuerpos de ayuda se escriben como párrafos continuos
# y es el widget quien los parte, de modo que una traducción más larga se ajusta
# sola en vez de descuadrar el tooltip.
_ANCHO_MAX: int = 470

_FONDO: str = "#2d2d2d"
_BORDE: str = "#4a4a4a"
_TEXTO: str = "#e0e0e0"
_TITULO: str = "#4A90E2"
_AVISO: str = "#FFA500"


class ToolTip:
    """Muestra un texto flotante al mantener el puntero sobre un widget."""

    def __init__(
        self,
        widget: Any,
        text: str,
        title: str = "",
        footer: str = "",
    ) -> None:
        self.widget: Any = widget
        self.text: str = text
        self.title: str = title
        # El pie se reserva para el estado de salud (falta una API key, falta el
        # binario...), que se resalta en ámbar por encima del texto de ayuda.
        self.footer: str = footer
        self.tooltip_window: tk.Toplevel | None = None
        self.id: str | None = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event: tk.Event | None = None) -> None:
        self.schedule()

    def leave(self, event: tk.Event | None = None) -> None:
        self.unschedule()
        self.hide()

    def schedule(self) -> None:
        self.unschedule()
        self.id = self.widget.after(_DELAY_MS, self.show)

    def unschedule(self) -> None:
        id_val: str | None = self.id
        self.id = None
        if id_val:
            self.widget.after_cancel(id_val)

    def show(self) -> None:
        if self.tooltip_window is not None:
            return

        x: int = self.widget.winfo_rootx() + 20
        y: int = self.widget.winfo_rooty() + self.widget.winfo_height() + 10

        ventana = tk.Toplevel(self.widget)
        ventana.wm_overrideredirect(True)
        ventana.wm_geometry(f"+{x}+{y}")
        ventana.configure(background=_BORDE)
        self.tooltip_window = ventana

        marco = tk.Frame(ventana, background=_FONDO)
        marco.pack(padx=1, pady=1, fill="both", expand=True)

        if self.title:
            tk.Label(
                marco,
                text=self.title,
                justify="left",
                anchor="w",
                background=_FONDO,
                foreground=_TITULO,
                font=("Helvetica", 10, "bold"),
                wraplength=_ANCHO_MAX,
            ).pack(fill="x", padx=9, pady=(7, 0))

        if self.text:
            tk.Label(
                marco,
                text=self.text,
                justify="left",
                anchor="w",
                background=_FONDO,
                foreground=_TEXTO,
                font=("Consolas", 10),
                wraplength=_ANCHO_MAX,
            ).pack(fill="x", padx=9, pady=(4 if self.title else 7, 7))

        if self.footer:
            tk.Label(
                marco,
                text=self.footer,
                justify="left",
                anchor="w",
                background=_FONDO,
                foreground=_AVISO,
                font=("Consolas", 10),
                wraplength=_ANCHO_MAX,
            ).pack(fill="x", padx=9, pady=(0, 7))

    def hide(self) -> None:
        tw: tk.Toplevel | None = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()


def attach(widget: Any, text: str, title: str = "", footer: str = "") -> None:
    """Asocia un tooltip al widget y a sus hijos.

    CustomTkinter compone sus controles con varios widgets internos; sin cubrir
    a los hijos, el tooltip no aparece al pasar sobre la etiqueta del control.
    """
    if not (text or title or footer):
        return
    ToolTip(widget, text, title=title, footer=footer)
    for child in widget.winfo_children():
        ToolTip(child, text, title=title, footer=footer)
