"""ToolTip flotante para los componentes de la interfaz."""

import tkinter as tk
from typing import Any

_DELAY_MS: int = 500


class ToolTip:
    """Muestra un texto flotante al mantener el puntero sobre un widget."""

    def __init__(self, widget: Any, text: str) -> None:
        self.widget: Any = widget
        self.text: str = text
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
        x: int = self.widget.winfo_rootx() + 20
        y: int = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label: tk.Label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify="left",
            background="#2d2d2d",
            foreground="white",
            relief="solid",
            borderwidth=1,
            font=("Consolas", 10),
        )
        label.pack(ipadx=5, ipady=3)

    def hide(self) -> None:
        tw: tk.Toplevel | None = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()


def attach(widget: Any, text: str) -> None:
    """Asocia un tooltip al widget y a sus hijos.

    CustomTkinter compone sus controles con varios widgets internos; sin cubrir
    a los hijos, el tooltip no aparece al pasar sobre la etiqueta del control.
    """
    if not text:
        return
    ToolTip(widget, text)
    for child in widget.winfo_children():
        ToolTip(child, text)
