"""Consola de salida: coloreado por prefijo, hipervínculos y exportación."""

import logging
import re
import tkinter as tk
import webbrowser
from typing import Any

import customtkinter as ctk
from customtkinter import filedialog

logger: logging.Logger = logging.getLogger(__name__)

_URL_PATTERN: re.Pattern[str] = re.compile(r"(https?://[^\s\)]+)")

# Prefijo emitido por los módulos -> etiqueta de color del textbox.
_TAG_BY_MARKER: tuple[tuple[str, str], ...] = (
    ("[*]", "info"),
    ("[+]", "success"),
    ("[-]", "error"),
    ("[!]", "error"),
    ("--- [", "header"),
)

_TAG_COLORS: dict[str, str] = {
    "info": "#569CD6",
    "success": "#4CAF50",
    "error": "#F44336",
    "header": "#C586C0",
}


class ConsoleView(ctk.CTkTextbox):
    """Textbox de solo lectura donde los módulos vuelcan sus resultados."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            state="disabled",
            fg_color="#1E1E1E",
            text_color="#D4D4D4",
            font=("Consolas", 13),
            **kwargs,
        )

        for tag, color in _TAG_COLORS.items():
            self.tag_config(tag, foreground=color)

        self.tag_config("hyperlink", foreground="#4A90E2", underline=True)
        self.tag_bind("hyperlink", "<Enter>", lambda e: self.configure(cursor="hand2"))
        self.tag_bind("hyperlink", "<Leave>", lambda e: self.configure(cursor=""))
        self.tag_bind("hyperlink", "<Button-1>", self._on_link_click)

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    @staticmethod
    def _tag_for(text: str) -> str | None:
        """Determina el color de la línea a partir del prefijo del módulo."""
        for marker, tag in _TAG_BY_MARKER:
            if marker in text:
                return tag
        return None

    def write(self, text: str) -> None:
        """Inserta texto respetando el color de la línea y marcando las URLs.

        Es el `callback` que reciben todos los módulos en `run()`.
        """
        self.configure(state="normal")
        tag: str | None = self._tag_for(text)

        last_idx: int = 0
        for match in _URL_PATTERN.finditer(text):
            start, end = match.span()
            if start > last_idx:
                self._insert(text[last_idx:start], tag)
            self._insert(text[start:end], "hyperlink")
            last_idx = end

        if last_idx < len(text):
            self._insert(text[last_idx:], tag)

        self.see("end")
        self.configure(state="disabled")

    def _insert(self, text: str, tag: str | None) -> None:
        if tag:
            self.insert("end", text, tag)
        else:
            self.insert("end", text)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def clear(self) -> None:
        self.configure(state="normal")
        self.delete("1.0", ctk.END)
        self.configure(state="disabled")

    @property
    def content(self) -> str:
        """Texto completo de la consola, sin el salto de línea final de Tk."""
        self.configure(state="normal")
        text: str = self.get("1.0", "end-1c")
        self.configure(state="disabled")
        return text

    def save_report(self) -> None:
        """Vuelca el contenido a un fichero elegido por el usuario."""
        content: str = self.content

        if not content.strip():
            self.write("[-] La consola está vacía, no hay nada que guardar.\n")
            return

        file_path: str = filedialog.asksaveasfilename(
            title="Guardar Reporte OSINT",
            defaultextension=".txt",
            filetypes=[
                ("Archivo de Texto Plano", "*.txt"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as err:
            logger.error("No se pudo guardar el reporte en disco: %s", err)
            self.write(f"\n[-] Error al intentar guardar en disco el reporte: {err}\n")
            return

        self.write(f"\n[+] -> REPORTE GUARDADO CON ÉXITO EN: {file_path} <-\n")

    # ------------------------------------------------------------------
    # Hipervínculos
    # ------------------------------------------------------------------

    def _on_link_click(self, event: tk.Event) -> None:
        index: str = self.index(f"@{event.x},{event.y}")
        ranges = self.tag_ranges("hyperlink")

        for i in range(0, len(ranges), 2):
            start, end = ranges[i], ranges[i + 1]
            if self.compare(start, "<=", index) and self.compare(index, "<=", end):
                url: str = self.get(start, end).strip()
                try:
                    webbrowser.open_new_tab(url)
                except webbrowser.Error as err:
                    logger.error(
                        "Error al interactuar con el navegador del sistema: %s", err
                    )
                break
