import asyncio
import logging
import os
import sys
import tkinter as tk
from typing import Any

import customtkinter as ctk
import psutil
from customtkinter import filedialog
from dotenv import load_dotenv

# ---- INTERCEPTOR MULTIPROCESO (SELF-EXECUTION) ----
# Si la app se llama a sí misma con esta bandera, ejecuta Holehe en modo consola
# en su propio proceso aislado y se cierra inmediatamente.
if len(sys.argv) > 1 and sys.argv[1] == "--run-holehe":
    from holehe import core

    sys.argv = ["holehe", sys.argv[2], "--only-used", "--no-color"]
    core.main()
    sys.exit(0)
# ---------------------------------------------------

# Cargar las claves de API del archivo .env de manera absoluta
env_path: str = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)


def validar_entorno() -> None:
    """Verifica el estado de las variables críticas sin llegar a romper el arranque de la app."""
    vt_key: str | None = os.getenv("VIRUSTOTAL_API_KEY")
    if not vt_key or len(vt_key.strip()) == 0 or vt_key.lower() == "tu_api_key_aqui":
        # Bajamos la severidad a WARNING y eliminamos el sys.exit
        logging.warning(
            "Aviso: VIRUSTOTAL_API_KEY no configurada en el .env. "
            "La aplicación iniciará, pero el módulo de VirusTotal mostrará un estado de alerta."
        )


# Se ejecuta la comprobación pasiva
validar_entorno()

# Importaciones de la Estructura Modular del Proyecto
from core.i18n import Translator  # noqa: E402
from core.logging_handler import CustomTkinterLogHandler  # noqa: E402
from modules.holehe_module import HoleheModule  # noqa: E402
from modules.metadata_module import MetadataModule  # noqa: E402
from modules.phoneinfoga_module import PhoneInfogaModule  # noqa: E402
from modules.port_scanner_module import PortScannerModule  # noqa: E402
from modules.security_headers_module import SecurityHeadersModule  # noqa: E402
from modules.sherlock_module import SherlockModule  # noqa: E402
from modules.subdomain_module import SubdomainModule  # noqa: E402
from modules.virustotal_module import VirustotalModule  # noqa: E402
from modules.wayback_module import WaybackModule  # noqa: E402
from modules.whois_dns_module import WhoisDnsModule  # noqa: E402

# Configuración estética global
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ToolTip:
    """Clase auxiliar para renderizar ToolTips flotantes sobre los componentes de la interfaz."""

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
        self.id = self.widget.after(500, self.show)

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


class OSINTApp(ctk.CTk):
    """Clase principal de la aplicación OSINT-Utility V2."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self.loop: asyncio.AbstractEventLoop = loop

        self.translator: Translator = Translator("ES")
        self.title(self.translator.get("app_title"))
        self.geometry("950x740")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Inicialización de instancias de módulos analíticos
        self.holehe_module: HoleheModule = HoleheModule()
        self.sherlock_module: SherlockModule = SherlockModule()
        self.virustotal_module: VirustotalModule = VirustotalModule()
        self.whois_module: WhoisDnsModule = WhoisDnsModule()
        self.subdomain_module: SubdomainModule = SubdomainModule()
        self.port_scanner_module: PortScannerModule = PortScannerModule()
        self.wayback_module: WaybackModule = WaybackModule()
        self.metadata_module: MetadataModule = MetadataModule()
        self.security_headers_module: SecurityHeadersModule = SecurityHeadersModule()
        self.phoneinfoga_module: PhoneInfogaModule = PhoneInfogaModule()

        self.current_task: asyncio.Task[Any] | None = None
        self.is_running: bool = True
        self._rebuilding: bool = False

        # Mapeo O(1) para evitar bifurcaciones complejas if/elif en runtime
        self._module_map: dict[str, Any] = {
            "Holehe": self.holehe_module,
            "Sherlock": self.sherlock_module,
            "PhoneInfoga": self.phoneinfoga_module,
            "VirusTotal": self.virustotal_module,
            "WHOIS": self.whois_module,
            "Subdominios": self.subdomain_module,
            "PortScanner": self.port_scanner_module,
            "SecurityHeaders": self.security_headers_module,
            "Wayback": self.wayback_module,
            "Metadatos": self.metadata_module,
        }

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- HEADER PRINCIPAL ---
        self.header_frame: ctk.CTkFrame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Opciones de idioma
        self.lang_var: ctk.StringVar = ctk.StringVar(value=self.translator.lang)
        self.lang_menu: ctk.CTkOptionMenu = ctk.CTkOptionMenu(
            self.header_frame,
            values=["ES", "EN"],
            variable=self.lang_var,
            command=self._change_language,
            width=60,
            height=25,
        )
        self.lang_menu.grid(row=0, column=4, sticky="ne", padx=5, pady=5)

        # Tabview para categorizar herramientas
        self.tabview: ctk.CTkTabview = ctk.CTkTabview(
            self.header_frame, command=self._on_tab_change, height=80
        )
        self.tabview.grid(
            row=1, column=0, columnspan=5, padx=10, pady=(5, 10), sticky="ew"
        )

        self.tabview.add(self.translator.get("tab_identities"))
        self.tabview.add(self.translator.get("tab_network"))
        self.tabview.add(self.translator.get("tab_forensics"))

        def _add_tool_radio(
            tab_name: str,
            text_base: str,
            var: ctk.StringVar,
            value: str,
            module: Any,
            padx: int = 10,
        ) -> ctk.CTkRadioButton:
            status, msg_key = module.check_health()
            msg: str = self.translator.get(msg_key) if msg_key else ""
            text_color: str | None = None
            if status == "ok":
                emoji = " 🟢"
                text_color = "#4CAF50"
            elif status == "warning":
                emoji = " 🟠"
                text_color = "#FFA500"
            elif status == "error":
                emoji = " 🔴"
                text_color = "#F44336"
            else:
                emoji = ""

            rb: ctk.CTkRadioButton = ctk.CTkRadioButton(
                self.tabview.tab(tab_name),
                text=text_base + emoji,
                variable=var,
                value=value,
                command=self._on_tool_change,
            )
            if text_color:
                rb.configure(text_color=text_color)
            rb.pack(side="left", padx=padx, pady=10)

            if msg:
                ToolTip(rb, msg)
                for child in rb.winfo_children():
                    ToolTip(child, msg)
            return rb

        # Pestaña Identidades
        self.identidades_var: ctk.StringVar = ctk.StringVar(value="Holehe")
        _add_tool_radio(
            self.translator.get("tab_identities"),
            self.translator.get("holehe_desc"),
            self.identidades_var,
            "Holehe",
            self.holehe_module,
            padx=20,
        )
        _add_tool_radio(
            self.translator.get("tab_identities"),
            self.translator.get("sherlock_desc"),
            self.identidades_var,
            "Sherlock",
            self.sherlock_module,
            padx=20,
        )
        _add_tool_radio(
            self.translator.get("tab_identities"),
            self.translator.get("phoneinfoga_desc"),
            self.identidades_var,
            "PhoneInfoga",
            self.phoneinfoga_module,
            padx=20,
        )

        # Pestaña Red
        self.red_var: ctk.StringVar = ctk.StringVar(value="VirusTotal")
        _add_tool_radio(
            self.translator.get("tab_network"),
            self.translator.get("virustotal_desc"),
            self.red_var,
            "VirusTotal",
            self.virustotal_module,
        )
        _add_tool_radio(
            self.translator.get("tab_network"),
            self.translator.get("whois_desc"),
            self.red_var,
            "WHOIS",
            self.whois_module,
        )
        _add_tool_radio(
            self.translator.get("tab_network"),
            self.translator.get("subdomains_desc"),
            self.red_var,
            "Subdominios",
            self.subdomain_module,
        )
        _add_tool_radio(
            self.translator.get("tab_network"),
            self.translator.get("ports_desc"),
            self.red_var,
            "PortScanner",
            self.port_scanner_module,
        )
        _add_tool_radio(
            self.translator.get("tab_network"),
            self.translator.get("headers_desc"),
            self.red_var,
            "SecurityHeaders",
            self.security_headers_module,
        )

        # Pestaña Forense
        self.forense_var: ctk.StringVar = ctk.StringVar(value="Metadatos")
        _add_tool_radio(
            self.translator.get("tab_forensics"),
            self.translator.get("metadata_desc"),
            self.forense_var,
            "Metadatos",
            self.metadata_module,
            padx=20,
        )
        _add_tool_radio(
            self.translator.get("tab_forensics"),
            self.translator.get("wayback_desc"),
            self.forense_var,
            "Wayback",
            self.wayback_module,
            padx=20,
        )

        # Contenedor del Buscador
        self.search_bar_frame: ctk.CTkFrame = ctk.CTkFrame(
            self.header_frame, fg_color="transparent"
        )
        self.search_bar_frame.grid(
            row=2, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew"
        )
        self.search_bar_frame.grid_columnconfigure(0, weight=1)

        self.target_entry: ctk.CTkEntry = ctk.CTkEntry(
            self.search_bar_frame,
            placeholder_text=self.translator.get("placeholder_holehe"),
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

        # --- CONSOLA CENTRAL ---
        self.console_textbox: ctk.CTkTextbox = ctk.CTkTextbox(
            self,
            state="disabled",
            fg_color="#1E1E1E",
            text_color="#D4D4D4",
            font=("Consolas", 13),
        )
        self.console_textbox.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")

        self.console_textbox.tag_config("info", foreground="#569CD6")
        self.console_textbox.tag_config("success", foreground="#4CAF50")
        self.console_textbox.tag_config("error", foreground="#F44336")
        self.console_textbox.tag_config("header", foreground="#C586C0")

        # --- FOOTER ---
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

        # --- ACOPLAMIENTO CENTRALIZADO DEL LOGGING HANDLER ---
        root_logger: logging.Logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        log_handler: CustomTkinterLogHandler = CustomTkinterLogHandler(
            self.console_textbox
        )
        log_formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(message)s", "%H:%M:%S"
        )
        log_handler.setFormatter(log_formatter)
        root_logger.addHandler(log_handler)

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

    def _on_tab_change(self) -> None:
        if not getattr(self, "_rebuilding", False):
            self._on_tool_change()

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

    def _get_active_tool_name(self) -> str:
        current_tab: str = self.tabview.get()
        if current_tab == self.translator.get("tab_identities"):
            return self.identidades_var.get()
        elif current_tab == self.translator.get("tab_network"):
            return self.red_var.get()
        elif current_tab == self.translator.get("tab_forensics"):
            return self.forense_var.get()
        return ""

    def _on_tool_change(self) -> None:
        choice: str = self._get_active_tool_name()

        def set_placeholder(text: str) -> None:
            current_val: str = self.target_entry.get()
            self.focus()
            self.target_entry.configure(placeholder_text=text)
            if not current_val:
                self.target_entry.delete(0, "end")

        _placeholder_keys: dict[str, str] = {
            "Holehe": "placeholder_holehe",
            "Sherlock": "placeholder_sherlock",
            "PhoneInfoga": "placeholder_phoneinfoga",
            "VirusTotal": "placeholder_virustotal",
            "WHOIS": "placeholder_whois",
            "Subdominios": "placeholder_subdomains",
            "PortScanner": "placeholder_ports",
            "SecurityHeaders": "placeholder_headers",
            "Wayback": "placeholder_wayback",
            "Metadatos": "placeholder_metadata",
        }

        if choice == "Metadatos":
            self.btn_file.configure(state="normal")
        else:
            self.btn_file.configure(state="disabled")

        key: str | None = _placeholder_keys.get(choice)
        if key:
            set_placeholder(self.translator.get(key))

    def log_to_console(self, text: str) -> None:
        self.console_textbox.configure(state="normal")
        tag: str | None = None
        if "[*]" in text:
            tag = "info"
        elif "[+]" in text:
            tag = "success"
        elif "[-]" in text or "[!]" in text:
            tag = "error"
        elif "--- [" in text:
            tag = "header"

        if tag:
            self.console_textbox.insert("end", text, tag)
        else:
            self.console_textbox.insert("end", text)
        self.console_textbox.see("end")
        self.console_textbox.configure(state="disabled")

    def clear_console(self) -> None:
        self.console_textbox.configure(state="normal")
        self.console_textbox.delete("1.0", ctk.END)
        self.console_textbox.configure(state="disabled")

    def save_report(self) -> None:
        self.console_textbox.configure(state="normal")
        content: str = self.console_textbox.get("1.0", "end-1c")
        self.console_textbox.configure(state="disabled")

        if not content.strip():
            self.log_to_console("[-] La consola está vacía, no hay nada que guardar.\n")
            return

        file_path: str = filedialog.asksaveasfilename(
            title="Guardar Reporte OSINT",
            defaultextension=".txt",
            filetypes=[
                ("Archivo de Texto Plano", "*.txt"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log_to_console(
                    f"\n[+] -> REPORTE GUARDADO CON ÉXITO EN: {file_path} <-\n"
                )
            except OSError as err:
                self.log_to_console(
                    f"\n[-] Error al intentar guardar en disco el reporte: {err}\n"
                )

    def run_tool_action(self) -> None:
        target: str = self.target_entry.get().strip()
        if not target:
            self.log_to_console("[-] Por favor, ingresa un objetivo válido.\n")
            return

        selected_tool: str = self._get_active_tool_name()

        if selected_tool == "Metadatos":
            if not os.path.exists(target) or not os.path.isfile(target):
                self.log_to_console(
                    f"[-] Error: El archivo en la ruta '{target}' NO EXISTE o es un directorio.\n"
                )
                return

        self.btn_search.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.target_entry.configure(state="disabled")
        self.btn_file.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.btn_save.configure(state="disabled")

        active_module: Any = self._module_map.get(selected_tool)
        if active_module is None:
            self.log_to_console("[-] Módulo no detectado.\n")
            self._restore_ui_controls()
            return

        self.log_to_console(
            f"\n--- [ {active_module.name} TASK ] Iniciando para: {target} ---\n"
        )
        self.current_task = self.loop.create_task(
            self._async_module_execution(active_module, target)
        )

    def cancel_action(self) -> None:
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()

    async def _async_module_execution(self, module: Any, target: str) -> None:
        try:
            await module.run(target, self.log_to_console)
        except asyncio.CancelledError:
            self.log_to_console("\n[!] Tarea cancelada por el usuario.\n")
        except (RuntimeError, ValueError, OSError) as err:
            self.log_to_console(f"\n[!] Error de ejecución en {module.name}: {err}\n")
        finally:
            self.current_task = None
            self._restore_ui_controls()

    def _restore_ui_controls(self) -> None:
        self.btn_search.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.target_entry.configure(state="normal")
        self.btn_clear.configure(state="normal")
        self.btn_save.configure(state="normal")
        if self._get_active_tool_name() == "Metadatos":
            self.btn_file.configure(state="normal")

    def on_closing(self) -> None:
        self.is_running = False
        try:
            current_pid: int = os.getpid()
            parent: psutil.Process = psutil.Process(current_pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
        except psutil.Error:
            pass

        try:
            self.quit()
            self.destroy()
        except tk.TclError:
            pass


async def tkinter_async_loop() -> None:
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    app = OSINTApp(loop)

    app.report_callback_exception = lambda exc, val, tb: None

    try:
        while app.is_running:
            try:
                app.update()
            except tk.TclError:
                break
            await asyncio.sleep(0.02)
    except tk.TclError:
        pass


if __name__ == "__main__":
    asyncio.run(tkinter_async_loop())
