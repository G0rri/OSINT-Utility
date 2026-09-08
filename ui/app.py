"""Ventana principal: ensambla los componentes y coordina la ejecución."""

import asyncio
import contextlib
import logging
import os
import tkinter as tk
from typing import Any

import customtkinter as ctk
import psutil
from customtkinter import filedialog

from core.base_module import BaseModule
from core.case import Caso, Entidad, Hallazgo, es_pivotable
from core.i18n import Translator
from core.logging_handler import CustomTkinterLogHandler
from core.registry import CATEGORIES, ToolRegistry, ToolSpec
from ui.console import ConsoleView
from ui.runner import TaskRunner
from ui.toolbar import ToolSelector

logger: logging.Logger = logging.getLogger(__name__)

_LANGUAGES: list[str] = ["ES", "EN"]
_LOG_FORMAT: str = "%(asctime)s - %(message)s"
_LOG_DATE_FORMAT: str = "%H:%M:%S"


class OSINTApp(ctk.CTk):
    """Panel central de OSINT-Utility V2."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self.loop: asyncio.AbstractEventLoop = loop

        self.translator: Translator = Translator("ES")
        self.registry: ToolRegistry = ToolRegistry()
        # Memoria de la investigación: sobrevive a los cambios de idioma y de
        # herramienta, y es lo que permite encadenar unas con otras.
        self.caso: Caso = Caso()

        self.title(self.translator.get("app_title"))
        self.geometry("950x740")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.is_running: bool = True
        self._rebuilding: bool = False
        self._log_handler: CustomTkinterLogHandler | None = None

        # Propiedad de la aplicación, no del selector: así el valor de cada
        # casilla sobrevive a la reconstrucción de la UI al cambiar de idioma.
        self._option_vars: dict[str, ctk.BooleanVar] = {}

        self.runner: TaskRunner = TaskRunner(
            loop=loop,
            write=self._write,
            on_start=self._lock_controls,
            on_finish=self._restore_ui_controls,
            on_result=self._ingerir_resultado,
        )

        self._build_ui()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_search_bar()

        self.console: ConsoleView = ConsoleView(
            self, on_entity_menu=self._mostrar_menu_entidad
        )
        self.console.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")

        self._build_footer()
        self._attach_log_handler()
        self._on_tool_change()

    def _build_header(self) -> None:
        self.header_frame: ctk.CTkFrame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.lang_var: ctk.StringVar = ctk.StringVar(value=self.translator.lang)
        self.lang_menu: ctk.CTkOptionMenu = ctk.CTkOptionMenu(
            self.header_frame,
            values=_LANGUAGES,
            variable=self.lang_var,
            command=self._change_language,
            width=60,
            height=25,
        )
        self.lang_menu.grid(row=0, column=4, sticky="ne", padx=5, pady=5)

        self.tools: ToolSelector = ToolSelector(
            self.header_frame,
            registry=self.registry,
            translator=self.translator,
            option_vars=self._option_vars,
            on_change=self._on_tool_change,
            height=80,
        )
        self.tools.grid(
            row=1, column=0, columnspan=5, padx=10, pady=(5, 10), sticky="ew"
        )

    def _build_search_bar(self) -> None:
        self.search_bar_frame: ctk.CTkFrame = ctk.CTkFrame(
            self.header_frame, fg_color="transparent"
        )
        self.search_bar_frame.grid(
            row=2, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew"
        )
        self.search_bar_frame.grid_columnconfigure(0, weight=1)

        default_tool: str = self.registry.default_for(CATEGORIES[0].key)
        default_spec: ToolSpec | None = self.registry.spec(default_tool)
        self.target_entry: ctk.CTkEntry = ctk.CTkEntry(
            self.search_bar_frame,
            placeholder_text=(
                self.translator.get(default_spec.placeholder_key)
                if default_spec is not None
                else ""
            ),
        )
        self.target_entry.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")

        self.btn_file: ctk.CTkButton = ctk.CTkButton(
            self.search_bar_frame,
            text="📂",
            width=30,
            command=self._open_file_dialog,
            state="disabled",
        )
        self.btn_file.grid(row=0, column=1, padx=(0, 10), pady=0)

        self.btn_search: ctk.CTkButton = ctk.CTkButton(
            self.search_bar_frame,
            text=self.translator.get("search_btn"),
            command=self.run_tool_action,
        )
        self.btn_search.grid(row=0, column=2, padx=(0, 10), pady=0)

        self.btn_stop: ctk.CTkButton = ctk.CTkButton(
            self.search_bar_frame,
            text=self.translator.get("stop_btn"),
            command=self.cancel_action,
            fg_color="red",
            state="disabled",
        )
        self.btn_stop.grid(row=0, column=3, padx=0, pady=0)

    def _build_footer(self) -> None:
        self.footer_frame: ctk.CTkFrame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.footer_frame.grid_columnconfigure(0, weight=1)

        self.btn_clear: ctk.CTkButton = ctk.CTkButton(
            self.footer_frame,
            text=self.translator.get("clear_btn"),
            fg_color="#8B0000",
            hover_color="#A52A2A",
            width=140,
            command=self.clear_console,
        )
        self.btn_clear.grid(row=0, column=1, padx=(0, 10))

        self.btn_save: ctk.CTkButton = ctk.CTkButton(
            self.footer_frame,
            text=self.translator.get("save_btn"),
            fg_color="#006400",
            hover_color="#228B22",
            width=140,
            command=self.save_report,
        )
        self.btn_save.grid(row=0, column=2)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _attach_log_handler(self) -> None:
        """Conecta la consola al logger raíz descartando siempre el handler previo.

        _build_ui se ejecuta de nuevo en cada cambio de idioma; sin este descarte
        los handlers se acumularían apuntando a widgets ya destruidos.
        """
        self._detach_log_handler()

        root_logger: logging.Logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        handler: CustomTkinterLogHandler = CustomTkinterLogHandler(self.console)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
        root_logger.addHandler(handler)
        self._log_handler = handler

    def _detach_log_handler(self) -> None:
        """Retira del logger raíz el handler de consola actualmente registrado."""
        if self._log_handler is not None:
            logging.getLogger().removeHandler(self._log_handler)
            self._log_handler.close()
            self._log_handler = None

    # ------------------------------------------------------------------
    # Consola
    # ------------------------------------------------------------------

    def _write(self, text: str) -> None:
        """Callback que reciben los módulos para volcar su salida."""
        self.console.write(text)

    def clear_console(self) -> None:
        self.console.clear()

    def save_report(self) -> None:
        self.console.save_report()

    # ------------------------------------------------------------------
    # Caso: ingesta de resultados y pivotado
    # ------------------------------------------------------------------

    def _ingerir_resultado(
        self, module: BaseModule, target: str, resultado: dict[str, Any]
    ) -> None:
        """Convierte el resultado de un módulo en hallazgos del caso."""
        spec: ToolSpec | None = self.registry.spec(self._clave_de(module))
        if spec is None:
            return

        try:
            extraidos = spec.extractor(resultado)
        except (KeyError, TypeError, ValueError) as err:
            logger.error("No se pudo extraer el resultado de %s: %s", spec.key, err)
            return

        nuevos: list[Hallazgo] = self.caso.incorporar(
            [
                Hallazgo(
                    tipo=tipo, valor=valor, origen=spec.key, desde=target, detalle=det
                )
                for tipo, valor, det in extraidos
            ]
        )

        if nuevos:
            accionables: int = sum(1 for h in nuevos if es_pivotable(h.tipo))
            self._write(
                f"\n[#] {len(nuevos)} hallazgos nuevos en el caso "
                f"({accionables} accionables con clic derecho). "
                f"Total acumulado: {len(self.caso)}.\n"
            )

        # Se remarca toda la consola: los hallazgos de esta ejecución y los que
        # ya se conocían de ejecuciones anteriores.
        self.console.marcar_entidades(self.caso.indice_por_valor())

    def _clave_de(self, module: BaseModule) -> str:
        """Clave de catálogo correspondiente a una instancia de módulo."""
        for spec in self.registry:
            if self.registry.module(spec.key) is module:
                return spec.key
        return ""

    def _mostrar_menu_entidad(
        self, valor: str, tipo: Entidad, x_root: int, y_root: int
    ) -> None:
        """Despliega las herramientas aplicables a un hallazgo concreto.

        El menú no está cableado: sale de preguntarle al catálogo qué acepta ese
        tipo de entidad.
        """
        menu: tk.Menu = tk.Menu(
            self, tearoff=0, bg="#2d2d2d", fg="white", activebackground="#1a6db5"
        )
        menu.add_command(label=f"{tipo.etiqueta}: {valor}", state="disabled")
        menu.add_separator()

        aplicables: list[ToolSpec] = self.registry.herramientas_para(tipo)
        if not aplicables:
            menu.add_command(label="Sin herramientas para este tipo", state="disabled")
        else:
            ocupado: bool = self.runner.is_running
            for spec in aplicables:
                menu.add_command(
                    label=self.translator.get(spec.label_key),
                    state="disabled" if ocupado else "normal",
                    command=lambda s=spec, v=valor: self._pivotar(s, v),
                )

        menu.add_separator()
        menu.add_command(
            label="Copiar", command=lambda: self._copiar_al_portapapeles(valor)
        )

        try:
            menu.tk_popup(x_root, y_root)
        finally:
            menu.grab_release()

    def _pivotar(self, spec: ToolSpec, valor: str) -> None:
        """Ejecuta una herramienta sobre un hallazgo del caso."""
        if self.runner.is_running:
            return

        self._seleccionar_herramienta(spec)
        self.target_entry.configure(state="normal")
        self.target_entry.delete(0, "end")
        self.target_entry.insert(0, valor)
        self._write(
            f"\n[>] Pivotando sobre {valor} con {self.translator.get(spec.label_key)}\n"
        )
        self.run_tool_action()

    def _seleccionar_herramienta(self, spec: ToolSpec) -> None:
        """Lleva la interfaz a la pestaña y el radio de una herramienta."""
        categoria = next((c for c in CATEGORIES if c.key == spec.category), None)
        if categoria is None:
            return
        self.tools.set(self.translator.get(categoria.label_key))
        self.tools.seleccionar(spec)
        self._on_tool_change()

    def _copiar_al_portapapeles(self, valor: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(valor)

    # ------------------------------------------------------------------
    # Selección de herramienta
    # ------------------------------------------------------------------

    def _on_tool_change(self) -> None:
        """Ajusta placeholder, botón de fichero y casillas a la herramienta activa."""
        spec: ToolSpec | None = self.tools.active_spec
        self.tools.refresh_options()

        self.btn_file.configure(
            state="normal" if spec is not None and spec.needs_file else "disabled"
        )

        if spec is None:
            return

        # Se mueve el foco fuera del campo: CustomTkinter oculta el placeholder
        # mientras la entrada está enfocada.
        self.focus()
        # configure() ya decide solo: si el usuario escribió algo lo respeta, y
        # si está vacía activa e inserta el nuevo texto. Borrar después dejaba
        # el campo en blanco con el placeholder marcado como activo.
        self.target_entry.configure(
            placeholder_text=self.translator.get(spec.placeholder_key)
        )

    def _change_language(self, new_lang: str) -> None:
        self.translator.load_lang(new_lang)
        self.title(self.translator.get("app_title"))
        self._rebuilding = True

        for widget in self.winfo_children():
            widget.destroy()

        def _do_rebuild() -> None:
            self._build_ui()
            self._rebuilding = False

        self.after(0, _do_rebuild)

    def _open_file_dialog(self) -> None:
        file_path: str = filedialog.askopenfilename(
            title="Seleccionar archivo para extraer metadatos",
            filetypes=[
                ("Archivos Multimedia/Docs", "*.jpg *.jpeg *.png *.tiff *.webp *.pdf"),
                ("Cualquier Archivo", "*.*"),
            ],
        )
        if file_path:
            self.target_entry.delete(0, ctk.END)
            self.target_entry.insert(0, file_path)

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------

    def run_tool_action(self) -> None:
        target: str = self.target_entry.get().strip()
        if not target:
            self._write("[-] Por favor, ingresa un objetivo válido.\n")
            return

        spec: ToolSpec | None = self.tools.active_spec
        if spec is None:
            self._write("[-] Módulo no detectado.\n")
            return

        if spec.needs_file and not os.path.isfile(target):
            self._write(
                f"[-] Error: El archivo en la ruta '{target}' NO EXISTE "
                "o es un directorio.\n"
            )
            return

        module = self.registry.module(spec.key)
        if module is None:
            self._write("[-] Módulo no detectado.\n")
            return

        self.tools.apply_options(module)
        self.runner.start(module, target)

    def cancel_action(self) -> None:
        self.runner.cancel()

    def _lock_controls(self) -> None:
        self.btn_search.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.target_entry.configure(state="disabled")
        self.btn_file.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.btn_save.configure(state="disabled")

    def _restore_ui_controls(self) -> None:
        self.btn_search.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.target_entry.configure(state="normal")
        self.btn_clear.configure(state="normal")
        self.btn_save.configure(state="normal")

        spec: ToolSpec | None = self.tools.active_spec
        if spec is not None and spec.needs_file:
            self.btn_file.configure(state="normal")

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def on_closing(self) -> None:
        self.is_running = False
        self._detach_log_handler()

        try:
            parent: psutil.Process = psutil.Process(os.getpid())
            for child in parent.children(recursive=True):
                with contextlib.suppress(psutil.NoSuchProcess):
                    child.kill()
        except psutil.Error as err:
            logger.debug("No se pudo enumerar el árbol de procesos: %s", err)

        with contextlib.suppress(tk.TclError):
            self.quit()
            self.destroy()
