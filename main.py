import sys
import os
import psutil
import json
import datetime

# ---- INTERCEPTOR MULTIPROCESO (SELF-EXECUTION) ----
# Si la app se llama a sí misma con esta bandera, ejecuta Holehe en modo consola
# en su propio proceso aislado y se cierra, sin llegar a cargar la interfaz.
if len(sys.argv) > 1 and sys.argv[1] == "--run-holehe":
    from holehe import core
    sys.argv = ["holehe", sys.argv[2], "--only-used", "--no-color"]
    core.main()
    sys.exit(0)
# ---------------------------------------------------

import asyncio
from dotenv import load_dotenv
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog as tk_filedialog
from customtkinter import filedialog

# ---- Historia de búsquedas ----
_HISTORY_FILE = os.path.join(os.path.dirname(__file__), ".search_history.json")
_MAX_HISTORY = 20

def _load_history() -> list:
    try:
        if os.path.exists(_HISTORY_FILE):
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_history(history: list):
    try:
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[:_MAX_HISTORY], f, ensure_ascii=False)
    except Exception:
        pass

def _add_to_history(target: str, tool: str, history: list) -> list:
    """Añade una entrada al historial; elimina duplicados exactos y limita a _MAX_HISTORY."""
    entry = {"target": target, "tool": tool, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    # Deduplicar por (target, tool)
    history = [h for h in history if not (h.get("target") == target and h.get("tool") == tool)]
    history.insert(0, entry)
    return history[:_MAX_HISTORY]


class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.show)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def show(self):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#2d2d2d", foreground="white", relief='solid', borderwidth=1,
                         font=("Consolas", 10))
        label.pack(ipadx=5, ipady=3)

    def hide(self):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()


# Cargar las claves de API del archivo .env al entorno de manera absoluta
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# ---- Estructura Modular ----
from modules.holehe_module import HoleheModule
from modules.sherlock_module import SherlockModule
from modules.virustotal_module import VirustotalModule
from modules.whois_dns_module import WhoisDnsModule
from modules.subdomain_module import SubdomainModule
from modules.port_scanner_module import PortScannerModule
from modules.wayback_module import WaybackModule
from modules.metadata_module import MetadataModule
from modules.security_headers_module import SecurityHeadersModule
from modules.phoneinfoga_module import PhoneInfogaModule
from core.i18n import Translator

# Configuración global
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---- Lazy Module Factory ----
# Los módulos solo se instancian cuando se usan por primera vez
_MODULE_CLASSES = {
    "Holehe":          HoleheModule,
    "Sherlock":        SherlockModule,
    "PhoneInfoga":     PhoneInfogaModule,
    "VirusTotal":      VirustotalModule,
    "WHOIS":           WhoisDnsModule,
    "Subdominios":     SubdomainModule,
    "PortScanner":     PortScannerModule,
    "SecurityHeaders": SecurityHeadersModule,
    "Wayback":         WaybackModule,
    "Metadatos":       MetadataModule,
}

class LazyModuleProxy:
    """Crea el módulo real solo en el primer acceso."""
    def __init__(self, cls):
        self._cls = cls
        self._instance = None

    def _get(self):
        if self._instance is None:
            self._instance = self._cls()
        return self._instance

    def check_health(self):
        return self._get().check_health()

    async def run(self, target, callback):
        return await self._get().run(target, callback)

    @property
    def name(self):
        return self._get().name


class OSINTApp(ctk.CTk):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop

        self.translator = Translator("ES")
        self.title(self.translator.get("app_title"))
        self.geometry("950x780")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ---- Lazy init de todos los módulos ----
        self._module_map = {key: LazyModuleProxy(cls) for key, cls in _MODULE_CLASSES.items()}

        self.current_task = None
        self.is_running = True
        self._rebuilding = False
        self._history = _load_history()
        self._history_index = -1  # para navegar con flechas

        self._build_ui()

    # ------------------------------------------------------------------
    # CONSTRUCCIÓN DE LA UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- HEADER PRINCIPAL ---
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Opciones de idioma
        self.lang_var = ctk.StringVar(value=self.translator.lang)
        self.lang_menu = ctk.CTkOptionMenu(
            self.header_frame,
            values=["ES", "EN"],
            variable=self.lang_var,
            command=self._change_language,
            width=60, height=25
        )
        self.lang_menu.grid(row=0, column=4, sticky="ne", padx=5, pady=5)

        # Tabview para categorizar herramientas
        self.tabview = ctk.CTkTabview(self.header_frame, command=self._on_tab_change, height=80)
        self.tabview.grid(row=1, column=0, columnspan=5, padx=10, pady=(5, 10), sticky="ew")

        self.tabview.add(self.translator.get("tab_identities"))
        self.tabview.add(self.translator.get("tab_network"))
        self.tabview.add(self.translator.get("tab_forensics"))

        def _add_tool_radio(tab_name, text_base, var, value, module, padx=10):
            status, msg_key = module.check_health()
            msg = self.translator.get(msg_key) if msg_key else ""
            text_color = None
            if status == "ok":
                emoji = " 🟢"; text_color = "#4CAF50"
            elif status == "warning":
                emoji = " 🟠"; text_color = "#FFA500"
            elif status == "error":
                emoji = " 🔴"; text_color = "#F44336"
            else:
                emoji = ""
            rb = ctk.CTkRadioButton(self.tabview.tab(tab_name), text=text_base + emoji,
                                    variable=var, value=value, command=self._on_tool_change)
            if text_color:
                rb.configure(text_color=text_color)
            rb.pack(side="left", padx=padx, pady=10)
            if msg:
                ToolTip(rb, msg)
                for child in rb.winfo_children():
                    ToolTip(child, msg)
            return rb

        # Pestaña Identidades
        self.identidades_var = ctk.StringVar(value="Holehe")
        _add_tool_radio(self.translator.get("tab_identities"), self.translator.get("holehe_desc"),
                        self.identidades_var, "Holehe", self._module_map["Holehe"], padx=20)
        _add_tool_radio(self.translator.get("tab_identities"), self.translator.get("sherlock_desc"),
                        self.identidades_var, "Sherlock", self._module_map["Sherlock"], padx=20)
        _add_tool_radio(self.translator.get("tab_identities"), self.translator.get("phoneinfoga_desc"),
                        self.identidades_var, "PhoneInfoga", self._module_map["PhoneInfoga"], padx=20)

        # Pestaña Red
        self.red_var = ctk.StringVar(value="VirusTotal")
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("virustotal_desc"),
                        self.red_var, "VirusTotal", self._module_map["VirusTotal"])
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("whois_desc"),
                        self.red_var, "WHOIS", self._module_map["WHOIS"])
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("subdomains_desc"),
                        self.red_var, "Subdominios", self._module_map["Subdominios"])
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("ports_desc"),
                        self.red_var, "PortScanner", self._module_map["PortScanner"])
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("headers_desc"),
                        self.red_var, "SecurityHeaders", self._module_map["SecurityHeaders"])

        # Pestaña Forense
        self.forense_var = ctk.StringVar(value="Metadatos")
        _add_tool_radio(self.translator.get("tab_forensics"), self.translator.get("metadata_desc"),
                        self.forense_var, "Metadatos", self._module_map["Metadatos"], padx=20)
        _add_tool_radio(self.translator.get("tab_forensics"), self.translator.get("wayback_desc"),
                        self.forense_var, "Wayback", self._module_map["Wayback"], padx=20)

        # Barra de búsqueda
        self.search_bar_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.search_bar_frame.grid(row=2, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew")
        self.search_bar_frame.grid_columnconfigure(0, weight=1)

        self.target_entry = ctk.CTkEntry(
            self.search_bar_frame,
            placeholder_text=self.translator.get("placeholder_holehe")
        )
        self.target_entry.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        # Navegación con flechas en el historial
        self.target_entry.bind("<Up>",   self._history_prev)
        self.target_entry.bind("<Down>", self._history_next)

        self.btn_file = ctk.CTkButton(
            self.search_bar_frame, text="📂", width=30,
            command=self._open_file_dialog, state="disabled"
        )
        self.btn_file.grid(row=0, column=1, padx=(0, 5), pady=0)

        # Botón historial
        self.btn_history = ctk.CTkButton(
            self.search_bar_frame, text="🕐", width=30,
            command=self._show_history_menu
        )
        self.btn_history.grid(row=0, column=2, padx=(0, 10), pady=0)
        ToolTip(self.btn_history, self.translator.get("history_tooltip"))

        self.btn_search = ctk.CTkButton(
            self.search_bar_frame,
            text=self.translator.get("search_btn"),
            command=self.run_tool_action
        )
        self.btn_search.grid(row=0, column=3, padx=(0, 10), pady=0)

        self.btn_stop = ctk.CTkButton(
            self.search_bar_frame,
            text=self.translator.get("stop_btn"),
            command=self.cancel_action,
            fg_color="red", state="disabled"
        )
        self.btn_stop.grid(row=0, column=4, padx=0, pady=0)

        # --- CONSOLA CENTRAL ---
        self.console_textbox = ctk.CTkTextbox(
            self, state="disabled", fg_color="#1E1E1E",
            text_color="#D4D4D4", font=("Consolas", 13)
        )
        self.console_textbox.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")

        self.console_textbox.tag_config("info",    foreground="#569CD6")
        self.console_textbox.tag_config("success", foreground="#4CAF50")
        self.console_textbox.tag_config("error",   foreground="#F44336")
        self.console_textbox.tag_config("header",  foreground="#C586C0")

        # --- FOOTER ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.footer_frame.grid_columnconfigure(0, weight=1)

        self.btn_clear = ctk.CTkButton(
            self.footer_frame,
            text=self.translator.get("clear_btn"),
            fg_color="#8B0000", hover_color="#A52A2A",
            width=140, command=self.clear_console
        )
        self.btn_clear.grid(row=0, column=1, padx=(0, 10))

        self.btn_save = ctk.CTkButton(
            self.footer_frame,
            text=self.translator.get("save_btn"),
            fg_color="#006400", hover_color="#228B22",
            width=140, command=self._show_save_menu
        )
        self.btn_save.grid(row=0, column=2, padx=(0, 10))

        # Botón exportar (JSON/HTML)
        self.btn_export = ctk.CTkButton(
            self.footer_frame,
            text=self.translator.get("export_btn"),
            fg_color="#1a4f7a", hover_color="#1d6fa5",
            width=160, command=self._show_export_menu
        )
        self.btn_export.grid(row=0, column=3)

    # ------------------------------------------------------------------
    # HISTORIAL DE BÚSQUEDAS
    # ------------------------------------------------------------------
    def _history_prev(self, event=None):
        """Flecha arriba → retrocede en el historial."""
        if not self._history:
            return
        self._history_index = min(self._history_index + 1, len(self._history) - 1)
        self._fill_from_history(self._history_index)

    def _history_next(self, event=None):
        """Flecha abajo → avanza en el historial."""
        if self._history_index <= 0:
            self._history_index = -1
            self.target_entry.delete(0, "end")
            return
        self._history_index -= 1
        self._fill_from_history(self._history_index)

    def _fill_from_history(self, idx: int):
        entry = self._history[idx]
        self.target_entry.delete(0, "end")
        self.target_entry.insert(0, entry["target"])

    def _show_history_menu(self):
        """Muestra un menú contextual con las últimas búsquedas."""
        if not self._history:
            self.log_to_console(f"[*] {self.translator.get('history_empty')}\n")
            return
        menu = tk.Menu(self, tearoff=0, background="#2d2d2d", foreground="white",
                       activebackground="#3a3a3a", activeforeground="white")
        for entry in self._history[:10]:
            label = f"[{entry.get('tool','?')}] {entry['target']}  ({entry.get('ts','')})"
            target = entry["target"]
            menu.add_command(label=label, command=lambda t=target: self._select_history_item(t))
        menu.add_separator()
        menu.add_command(label=self.translator.get("history_clear"),
                         command=self._clear_history)
        try:
            menu.tk_popup(self.btn_history.winfo_rootx(),
                          self.btn_history.winfo_rooty() + self.btn_history.winfo_height())
        finally:
            menu.grab_release()

    def _select_history_item(self, target: str):
        self.target_entry.delete(0, "end")
        self.target_entry.insert(0, target)

    def _clear_history(self):
        self._history = []
        _save_history(self._history)
        self.log_to_console(f"[*] {self.translator.get('history_cleared')}\n")

    # ------------------------------------------------------------------
    # GUARDADO / EXPORTACIÓN
    # ------------------------------------------------------------------
    def _show_save_menu(self):
        """Muestra menú: guardar como TXT (comportamiento original)."""
        self.save_report()

    def _show_export_menu(self):
        """Muestra menú contextual para elegir formato de exportación."""
        menu = tk.Menu(self, tearoff=0, background="#2d2d2d", foreground="white",
                       activebackground="#3a3a3a", activeforeground="white")
        menu.add_command(label="JSON (.json)", command=lambda: self._export("json"))
        menu.add_command(label="HTML (.html)", command=lambda: self._export("html"))
        try:
            menu.tk_popup(self.btn_export.winfo_rootx(),
                          self.btn_export.winfo_rooty() + self.btn_export.winfo_height())
        finally:
            menu.grab_release()

    def save_report(self):
        """Guarda la consola como archivo .txt (comportamiento original)."""
        self.console_textbox.configure(state="normal")
        content = self.console_textbox.get("1.0", "end-1c")
        self.console_textbox.configure(state="disabled")
        if not content.strip():
            self.log_to_console(f"[-] {self.translator.get('save_empty')}\n")
            return
        file_path = filedialog.asksaveasfilename(
            title=self.translator.get("save_dialog_title"),
            defaultextension=".txt",
            filetypes=[("Archivo de Texto Plano", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log_to_console(f"\n[+] -> {self.translator.get('save_ok')} {file_path} <-\n")
            except Exception as e:
                self.log_to_console(f"\n[-] {self.translator.get('save_error')} {e}\n")

    def _export(self, fmt: str):
        """Exporta el contenido de la consola a JSON o HTML."""
        self.console_textbox.configure(state="normal")
        content = self.console_textbox.get("1.0", "end-1c")
        self.console_textbox.configure(state="disabled")
        if not content.strip():
            self.log_to_console(f"[-] {self.translator.get('save_empty')}\n")
            return

        if fmt == "json":
            self._export_json(content)
        elif fmt == "html":
            self._export_html(content)

    def _export_json(self, content: str):
        file_path = filedialog.asksaveasfilename(
            title=self.translator.get("export_json_title"),
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        lines = [l for l in content.splitlines() if l.strip()]
        data = {
            "tool": self._get_active_tool_name(),
            "timestamp": datetime.datetime.now().isoformat(),
            "results": lines
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log_to_console(f"\n[+] -> {self.translator.get('export_ok')} {file_path} <-\n")
        except Exception as e:
            self.log_to_console(f"\n[-] {self.translator.get('export_error')} {e}\n")

    def _export_html(self, content: str):
        file_path = filedialog.asksaveasfilename(
            title=self.translator.get("export_html_title"),
            defaultextension=".html",
            filetypes=[("HTML", "*.html"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return

        COLOR_MAP = {
            "[*]":   "#569CD6",
            "[+]":   "#4CAF50",
            "[-]":   "#F44336",
            "[!]":   "#F44336",
            "--- [": "#C586C0",
        }

        def colorize(line: str) -> str:
            import html as _html
            safe = _html.escape(line)
            for prefix, color in COLOR_MAP.items():
                if prefix in line:
                    return f'<span style="color:{color}">{safe}</span>'
            return safe

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tool = self._get_active_tool_name()
        rows = "\n".join(f"<div class='line'>{colorize(l)}</div>" for l in content.splitlines())

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>OSINT Report – {tool}</title>
<style>
  body {{ background:#1E1E1E; color:#D4D4D4; font-family:Consolas,monospace; padding:20px; }}
  h1 {{ color:#C586C0; font-size:1.2em; }}
  .meta {{ color:#888; font-size:.85em; margin-bottom:16px; }}
  .console {{ background:#111; border:1px solid #333; padding:16px; border-radius:6px; line-height:1.6; }}
  .line {{ white-space:pre-wrap; word-break:break-all; }}
</style>
</head>
<body>
<h1>OSINT V2 – {tool}</h1>
<div class="meta">Generado: {timestamp}</div>
<div class="console">
{rows}
</div>
</body>
</html>"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)
            self.log_to_console(f"\n[+] -> {self.translator.get('export_ok')} {file_path} <-\n")
        except Exception as e:
            self.log_to_console(f"\n[-] {self.translator.get('export_error')} {e}\n")

    # ------------------------------------------------------------------
    # IDIOMA
    # ------------------------------------------------------------------
    def _change_language(self, new_lang: str):
        self.translator.load_lang(new_lang)
        self.title(self.translator.get("app_title"))
        self._rebuilding = True
        for widget in self.winfo_children():
            widget.destroy()

        def _do_rebuild():
            self._build_ui()
            self._rebuilding = False

        self.after(0, _do_rebuild)

    # ------------------------------------------------------------------
    # NAVEGACIÓN DE TABS Y HERRAMIENTAS
    # ------------------------------------------------------------------
    def _get_active_tool_name(self):
        current_tab = self.tabview.get()
        if current_tab == self.translator.get("tab_identities"):
            return self.identidades_var.get()
        elif current_tab == self.translator.get("tab_network"):
            return self.red_var.get()
        elif current_tab == self.translator.get("tab_forensics"):
            return self.forense_var.get()
        return ""

    def _on_tool_change(self):
        choice = self._get_active_tool_name()
        self._history_index = -1  # Reiniciar navegación de historial

        def set_placeholder(text):
            current_val = self.target_entry.get()
            self.focus()
            self.target_entry.configure(placeholder_text=text)
            if not current_val:
                self.target_entry.delete(0, "end")

        _placeholder_keys = {
            "Holehe":          "placeholder_holehe",
            "Sherlock":        "placeholder_sherlock",
            "PhoneInfoga":     "placeholder_phoneinfoga",
            "VirusTotal":      "placeholder_virustotal",
            "WHOIS":           "placeholder_whois",
            "Subdominios":     "placeholder_subdomains",
            "PortScanner":     "placeholder_ports",
            "SecurityHeaders": "placeholder_headers",
            "Wayback":         "placeholder_wayback",
            "Metadatos":       "placeholder_metadata",
        }

        if choice == "Metadatos":
            self.btn_file.configure(state="normal")
        else:
            self.btn_file.configure(state="disabled")

        key = _placeholder_keys.get(choice)
        if key:
            set_placeholder(self.translator.get(key))

    def _on_tab_change(self):
        if not getattr(self, '_rebuilding', False):
            self._on_tool_change()

    # ------------------------------------------------------------------
    # CONSOLA
    # ------------------------------------------------------------------
    def log_to_console(self, text: str):
        self.console_textbox.configure(state="normal")
        tag = None
        if "[*]" in text:   tag = "info"
        elif "[+]" in text: tag = "success"
        elif "[-]" in text or "[!]" in text: tag = "error"
        elif "--- [" in text: tag = "header"
        if tag:
            self.console_textbox.insert("end", text, tag)
        else:
            self.console_textbox.insert("end", text)
        self.console_textbox.see("end")
        self.console_textbox.configure(state="disabled")

    def clear_console(self):
        self.console_textbox.configure(state="normal")
        self.console_textbox.delete("1.0", ctk.END)
        self.console_textbox.configure(state="disabled")

    # ------------------------------------------------------------------
    # EJECUCIÓN DE MÓDULOS
    # ------------------------------------------------------------------
    def _open_file_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo para extraer metadatos",
            filetypes=[("Archivos Multimedia/Docs", "*.jpg *.jpeg *.png *.tiff *.webp *.pdf"),
                       ("Cualquier Archivo", "*.*")]
        )
        if file_path:
            self.target_entry.delete(0, ctk.END)
            self.target_entry.insert(0, file_path)

    def run_tool_action(self):
        target = self.target_entry.get().strip()
        if not target:
            self.log_to_console(f"[-] {self.translator.get('error_empty_target')}\n")
            return

        selected_tool = self._get_active_tool_name()

        if selected_tool == "Metadatos":
            if not os.path.exists(target) or not os.path.isfile(target):
                self.log_to_console(f"[-] {self.translator.get('error_file_not_found')} '{target}'\n")
                return

        # Guardar en historial
        self._history = _add_to_history(target, selected_tool, self._history)
        _save_history(self._history)
        self._history_index = -1

        # Deshabilitar controles
        self.btn_search.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.target_entry.configure(state="disabled")
        self.btn_file.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.btn_save.configure(state="disabled")
        self.btn_export.configure(state="disabled")

        active_module = self._module_map.get(selected_tool)
        if active_module is None:
            self.log_to_console("[-] Módulo no detectado.\n")
            self._restore_ui_controls()
            return

        self.log_to_console(f"\n--- [ {active_module.name} TASK ] {self.translator.get('task_start')} {target} ---\n")
        self.current_task = self.loop.create_task(
            self._async_module_execution(active_module, target)
        )

    def cancel_action(self):
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()

    async def _async_module_execution(self, module, target: str):
        try:
            await module.run(target, self.log_to_console)
        except asyncio.CancelledError:
            self.log_to_console(f"\n[!] {self.translator.get('task_cancelled')}\n")
        except Exception as e:
            self.log_to_console(f"\n[!] {self.translator.get('task_error')} {module.name}: {e}\n")
        finally:
            self.current_task = None
            self._restore_ui_controls()

    def _restore_ui_controls(self):
        self.btn_search.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.target_entry.configure(state="normal")
        self.btn_clear.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.btn_export.configure(state="normal")
        if self._get_active_tool_name() == "Metadatos":
            self.btn_file.configure(state="normal")

    # ------------------------------------------------------------------
    # CIERRE SEGURO
    # ------------------------------------------------------------------
    def on_closing(self):
        self.is_running = False
        try:
            current_pid = os.getpid()
            parent = psutil.Process(current_pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            # Esperar hasta 2 s antes de matar a la fuerza
            _, still_alive = psutil.wait_procs(children, timeout=2)
            for child in still_alive:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
        except Exception:
            pass
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass


# ------------------------------------------------------------------
# LOOP PRINCIPAL
# ------------------------------------------------------------------
async def tkinter_async_loop():
    loop = asyncio.get_running_loop()
    app = OSINTApp(loop)
    app.report_callback_exception = lambda exc, val, tb: None
    try:
        while app.is_running:
            try:
                app.update()
            except Exception:
                break
            await asyncio.sleep(0.01)
    except Exception as e:
        if "application has been destroyed" not in str(e) and \
           "can't invoke \"update\" command" not in str(e):
            raise


if __name__ == "__main__":
    asyncio.run(tkinter_async_loop())
