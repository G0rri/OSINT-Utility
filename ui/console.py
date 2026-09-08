"""Consola de salida: coloreado por prefijo, hipervínculos y exportación."""

import logging
import re
import tkinter as tk
import webbrowser
from collections.abc import Callable
from typing import Any

import customtkinter as ctk
from customtkinter import filedialog

logger: logging.Logger = logging.getLogger(__name__)

_URL_PATTERN: re.Pattern[str] = re.compile(r"(https?://[^\s\)]+)")

# Prefijo emitido por los módulos -> etiqueta de color del textbox.
_TAG_BY_MARKER: tuple[tuple[str, str], ...] = (
    # Los avisos del caso van primero: deben distinguirse de la salida de los
    # módulos, porque hablan del estado de la investigación y no del escaneo.
    ("[#]", "caso"),
    ("[>]", "caso"),
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
    "caso": "#FFB74D",
}

# Marca aplicada sobre los hallazgos accionables del caso.
_ENTIDAD_TAG: str = "entidad"


class ConsoleView(ctk.CTkTextbox):
    """Textbox de solo lectura donde los módulos vuelcan sus resultados."""

    def __init__(
        self,
        master: Any,
        on_entity_menu: Callable[[str, Any, int, int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            state="disabled",
            fg_color="#1E1E1E",
            text_color="#D4D4D4",
            font=("Consolas", 13),
            **kwargs,
        )

        # Se invoca al pulsar el botón derecho sobre un hallazgo marcado.
        self._on_entity_menu = on_entity_menu
        self._entidades: dict[str, Any] = {}

        for tag, color in _TAG_COLORS.items():
            self.tag_config(tag, foreground=color)

        self.tag_config("hyperlink", foreground="#4A90E2", underline=True)
        self.tag_bind("hyperlink", "<Enter>", lambda e: self.configure(cursor="hand2"))
        self.tag_bind("hyperlink", "<Leave>", lambda e: self.configure(cursor=""))
        self.tag_bind("hyperlink", "<Button-1>", self._on_link_click)

        # Los hallazgos del caso se subrayan en ámbar: indican que hay acciones
        # disponibles sobre ellos con el botón derecho.
        self.tag_config(_ENTIDAD_TAG, foreground="#FFB74D", underline=True)
        self.tag_bind(_ENTIDAD_TAG, "<Enter>", lambda e: self.configure(cursor="hand2"))
        self.tag_bind(_ENTIDAD_TAG, "<Leave>", lambda e: self.configure(cursor=""))
        self.tag_bind(_ENTIDAD_TAG, "<Button-3>", self._on_entity_right_click)

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
        self._entidades = {}

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
    # Hallazgos accionables
    # ------------------------------------------------------------------

    def marcar_entidades(self, indice: dict[str, Any]) -> None:
        """Subraya en el texto ya escrito los valores conocidos del caso.

        Se buscan cadenas exactas que el caso ya conoce, no patrones: la consola
        no adivina qué es un dominio, se lo dice el caso. Los tramos ya marcados
        como hipervínculo se respetan para no pisar ese comportamiento.
        """
        self._entidades = dict(indice)
        if not indice:
            return

        texto: str = self.content
        # La búsqueda ignora mayúsculas: el caso guarda una forma canónica en
        # minúsculas (los registradores WHOIS devuelven los name servers en
        # mayúsculas), mientras que la consola muestra el texto tal como llegó.
        texto_lower: str = texto.lower()

        for valor in sorted(indice, key=len, reverse=True):
            if not valor:
                continue
            aguja: str = valor.lower()
            inicio: int = 0
            while True:
                pos: int = texto_lower.find(aguja, inicio)
                if pos < 0:
                    break
                inicio = pos + len(aguja)
                if self._es_limite(texto, pos, len(aguja)):
                    self.tag_add(
                        _ENTIDAD_TAG,
                        f"1.0 + {pos} chars",
                        f"1.0 + {pos + len(aguja)} chars",
                    )

    @staticmethod
    def _es_limite(texto: str, pos: int, largo: int) -> bool:
        """Evita marcar coincidencias dentro de una palabra mayor.

        Sin esto, `example.com` quedaría subrayado dentro de `mail.example.com`.
        """
        anterior: str = texto[pos - 1] if pos > 0 else " "
        siguiente_idx: int = pos + largo
        siguiente: str = texto[siguiente_idx] if siguiente_idx < len(texto) else " "
        return anterior not in "._-/:@" and siguiente not in "._-/@"

    def _on_entity_right_click(self, event: tk.Event) -> None:
        """Localiza el hallazgo bajo el cursor y pide su menú de acciones."""
        if self._on_entity_menu is None:
            return

        index: str = self.index(f"@{event.x},{event.y}")
        ranges = self.tag_ranges(_ENTIDAD_TAG)

        for i in range(0, len(ranges), 2):
            start, end = ranges[i], ranges[i + 1]
            if self.compare(start, "<=", index) and self.compare(index, "<=", end):
                mostrado: str = self.get(start, end).strip()
                # Se recupera la clave canónica del caso, no el texto mostrado.
                valor: str = mostrado
                tipo: Any = self._entidades.get(valor)
                if tipo is None:
                    for clave, t in self._entidades.items():
                        if clave.lower() == mostrado.lower():
                            valor, tipo = clave, t
                            break
                if tipo is not None:
                    self._on_entity_menu(valor, tipo, event.x_root, event.y_root)
                return

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
