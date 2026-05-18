import sys
import os
import psutil

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
from customtkinter import filedialog

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

class OSINTApp(ctk.CTk):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop
        
        self.translator = Translator("ES")
        self.title(self.translator.get("app_title"))
        self.geometry("950x740")  # Ligeramente más alta
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Inicialización de todos los 8 módulos
        self.holehe_module = HoleheModule()
        self.sherlock_module = SherlockModule()
        self.virustotal_module = VirustotalModule()
        self.whois_module = WhoisDnsModule()
        self.subdomain_module = SubdomainModule()
        self.port_scanner_module = PortScannerModule()
        self.wayback_module = WaybackModule()
        self.metadata_module = MetadataModule()
        self.security_headers_module = SecurityHeadersModule()
        self.phoneinfoga_module = PhoneInfogaModule()
        
        self.current_task = None
        self.is_running = True
        self._rebuilding = False  # Guardia para el cambio de idioma

        # Mapa nombre_herramienta → módulo (evita cadenas if/elif en runtime)
        self._module_map = {
            "Holehe":          self.holehe_module,
            "Sherlock":        self.sherlock_module,
            "PhoneInfoga":     self.phoneinfoga_module,
            "VirusTotal":      self.virustotal_module,
            "WHOIS":           self.whois_module,
            "Subdominios":     self.subdomain_module,
            "PortScanner":     self.port_scanner_module,
            "SecurityHeaders": self.security_headers_module,
            "Wayback":         self.wayback_module,
            "Metadatos":       self.metadata_module,
        }

        self._build_ui()

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
            width=60,
            height=25
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
                emoji = " 🟢"
                text_color = "#4CAF50" # Verde
            elif status == "warning":
                emoji = " 🟠"
                text_color = "#FFA500" # Naranja
            elif status == "error":
                emoji = " 🔴"
                text_color = "#F44336" # Rojo
            else:
                emoji = ""
                
            rb = ctk.CTkRadioButton(self.tabview.tab(tab_name), text=text_base + emoji, variable=var, value=value, command=self._on_tool_change)
            if text_color:
                rb.configure(text_color=text_color)
            rb.pack(side="left", padx=padx, pady=10)
            
            if msg:
                # Asociar el tooltip al propio label del widget y a la bolita
                ToolTip(rb, msg)
                # CustomTkinter usa componentes internos, para asegurar que el hover funcione sobre todo el widget:
                for child in rb.winfo_children():
                    ToolTip(child, msg)
            return rb
            
        # Pestaña Identidades
        self.identidades_var = ctk.StringVar(value="Holehe")
        _add_tool_radio(self.translator.get("tab_identities"), self.translator.get("holehe_desc"), self.identidades_var, "Holehe", self.holehe_module, padx=20)
        _add_tool_radio(self.translator.get("tab_identities"), self.translator.get("sherlock_desc"), self.identidades_var, "Sherlock", self.sherlock_module, padx=20)
        _add_tool_radio(self.translator.get("tab_identities"), self.translator.get("phoneinfoga_desc"), self.identidades_var, "PhoneInfoga", self.phoneinfoga_module, padx=20)
        
        # Pestaña Red
        self.red_var = ctk.StringVar(value="VirusTotal")
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("virustotal_desc"), self.red_var, "VirusTotal", self.virustotal_module)
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("whois_desc"), self.red_var, "WHOIS", self.whois_module)
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("subdomains_desc"), self.red_var, "Subdominios", self.subdomain_module)
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("ports_desc"), self.red_var, "PortScanner", self.port_scanner_module)
        _add_tool_radio(self.translator.get("tab_network"), self.translator.get("headers_desc"), self.red_var, "SecurityHeaders", self.security_headers_module)
        
        # Pestaña Forense
        self.forense_var = ctk.StringVar(value="Metadatos")
        _add_tool_radio(self.translator.get("tab_forensics"), self.translator.get("metadata_desc"), self.forense_var, "Metadatos", self.metadata_module, padx=20)
        _add_tool_radio(self.translator.get("tab_forensics"), self.translator.get("wayback_desc"), self.forense_var, "Wayback", self.wayback_module, padx=20)

        # Contenedor Inferior del Header para Buscador (Barra Entry + Botones)
        self.search_bar_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.search_bar_frame.grid(row=2, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew")
        self.search_bar_frame.grid_columnconfigure(0, weight=1)

        self.target_entry = ctk.CTkEntry(
            self.search_bar_frame, 
            placeholder_text=self.translator.get("placeholder_holehe")
        )
        self.target_entry.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        
        self.btn_file = ctk.CTkButton(
            self.search_bar_frame, 
            text="📂", 
            width=30,
            command=self._open_file_dialog,
            state="disabled"
        )
        self.btn_file.grid(row=0, column=1, padx=(0, 10), pady=0)

        self.btn_search = ctk.CTkButton(
            self.search_bar_frame, 
            text=self.translator.get("search_btn"), 
            command=self.run_tool_action
        )
        self.btn_search.grid(row=0, column=2, padx=(0, 10), pady=0)
        
        self.btn_stop = ctk.CTkButton(
            self.search_bar_frame, 
            text=self.translator.get("stop_btn"), 
            command=self.cancel_action,
            fg_color="red",
            state="disabled"
        )
        self.btn_stop.grid(row=0, column=3, padx=0, pady=0)
        
        # --- CONSOLA CENTRAL ---
        self.console_textbox = ctk.CTkTextbox(
            self, state="disabled", fg_color="#1E1E1E", text_color="#D4D4D4", font=("Consolas", 13)
        )
        self.console_textbox.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        
        # Sistema de etiquetas para colorear texto
        self.console_textbox.tag_config("info", foreground="#569CD6")      # Azul VSCode
        self.console_textbox.tag_config("success", foreground="#4CAF50")   # Verde suave
        self.console_textbox.tag_config("error", foreground="#F44336")     # Rojo
        self.console_textbox.tag_config("header", foreground="#C586C0")    # Magenta/Morado

        # --- FOOTER ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.footer_frame.grid_columnconfigure(0, weight=1)
        
        self.btn_clear = ctk.CTkButton(
            self.footer_frame,
            text=self.translator.get("clear_btn"),
            fg_color="#8B0000",
            hover_color="#A52A2A",
            width=140,
            command=self.clear_console
        )
        self.btn_clear.grid(row=0, column=1, padx=(0, 10))
        
        self.btn_save = ctk.CTkButton(
            self.footer_frame,
            text=self.translator.get("save_btn"),
            fg_color="#006400",
            hover_color="#228B22",
            width=140,
            command=self.save_report
        )
        self.btn_save.grid(row=0, column=2)

    def _open_file_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo para extraer metadatos",
            filetypes=[("Archivos Multimedia/Docs", "*.jpg *.jpeg *.png *.tiff *.webp *.pdf"), ("Cualquier Archivo", "*.*")]
        )
        if file_path:
            self.target_entry.delete(0, ctk.END)
            self.target_entry.insert(0, file_path)

    def _on_tab_change(self):
        if not getattr(self, '_rebuilding', False):
            self._on_tool_change()

    def _change_language(self, new_lang: str):
        self.translator.load_lang(new_lang)
        self.title(self.translator.get("app_title"))

        # Flag de guardia: evita que _on_tab_change / _on_tool_change
        # accedan a self.tabview mientras está siendo destruido y reconstruido.
        self._rebuilding = True

        # Destruir todos los hijos de la ventana raíz
        for widget in self.winfo_children():
            widget.destroy()

        # Diferir la construcción un ciclo de eventos para que Tkinter
        # procese completamente la destrucción antes de crear nuevos widgets.
        def _do_rebuild():
            self._build_ui()
            self._rebuilding = False

        self.after(0, _do_rebuild)

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

        # Mitigación para el bug de CustomTkinter donde el placeholder se vuelve texto editable
        def set_placeholder(text):
            current_val = self.target_entry.get()
            self.focus()  # Quitar foco del entry temporalmente
            self.target_entry.configure(placeholder_text=text)
            if not current_val:
                self.target_entry.delete(0, "end")

        # Mapa directo tool → clave i18n del placeholder (O(1) vs cadena if/elif)
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

    def log_to_console(self, text: str):
        self.console_textbox.configure(state="normal")
        
        # Aplicación automática de colores basados en los prefijos estándar del OSINT V2
        tag = None
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

    def clear_console(self):
        self.console_textbox.configure(state="normal")
        self.console_textbox.delete("1.0", ctk.END)
        self.console_textbox.configure(state="disabled")

    def save_report(self):
        self.console_textbox.configure(state="normal")
        content = self.console_textbox.get("1.0", "end-1c")
        self.console_textbox.configure(state="disabled")
        
        if not content.strip():
            self.log_to_console("[-] La consola está vacía, no hay nada que guardar.\n")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Guardar Reporte OSINT",
            defaultextension=".txt",
            filetypes=[("Archivo de Texto Plano", "*.txt"), ("Todos los archivos", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log_to_console(f"\n[+] -> REPORTE GUARDADO CON ÉXITO EN: {file_path} <-\n")
            except Exception as e:
                self.log_to_console(f"\n[-] Error al intentar guardar en disco el reporte: {str(e)}\n")

    def run_tool_action(self):
        target = self.target_entry.get().strip()
        if not target:
            self.log_to_console("[-] Por favor, ingresa un objetivo válido.\n")
            return
            
        selected_tool = self._get_active_tool_name()
        
        if selected_tool == "Metadatos":
            if not os.path.exists(target) or not os.path.isfile(target):
                self.log_to_console(f"[-] Error: El archivo en la ruta '{target}' NO EXISTE o es un directorio.\n")
                return
        
        # Disable buttons
        self.btn_search.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.target_entry.configure(state="disabled")
        self.btn_file.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.btn_save.configure(state="disabled")
        
        # Resolver módulo activo mediante dict (O(1), sin cadena if/elif)
        active_module = self._module_map.get(selected_tool)
        if active_module is None:
            self.log_to_console("[-] Módulo no detectado.\n")
            self._restore_ui_controls()
            return
            
        self.log_to_console(f"\n--- [ {active_module.name} TASK ] Iniciando para: {target} ---\n")
        self.current_task = self.loop.create_task(self._async_module_execution(active_module, target))

    def cancel_action(self):
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()

    async def _async_module_execution(self, module, target: str):
        try:
            await module.run(target, self.log_to_console)
        except asyncio.CancelledError:
            self.log_to_console("\n[!] Tarea cancelada por el usuario.\n")
        except Exception as e:
            self.log_to_console(f"\n[!] Error crítico ejecutando {module.name}: {e}\n")
        finally:
            self.current_task = None
            self._restore_ui_controls()

    def _restore_ui_controls(self):
        self.btn_search.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.target_entry.configure(state="normal")
        self.btn_clear.configure(state="normal")
        self.btn_save.configure(state="normal")
        if self._get_active_tool_name() == "Metadatos":
            self.btn_file.configure(state="normal")

    def on_closing(self):
        self.is_running = False
        try:
            current_pid = os.getpid()
            parent = psutil.Process(current_pid)
            for child in parent.children(recursive=True):
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

async def tkinter_async_loop():
    loop = asyncio.get_running_loop()
    app = OSINTApp(loop)
    
    # Suprimir los traceback de callbacks que ocurren cuando la ventana se está destruyendo
    app.report_callback_exception = lambda exc, val, tb: None
    
    try:
        while app.is_running:
            try:
                app.update()               
            except Exception:
                break
            await asyncio.sleep(0.01)
    except Exception as e:
        if "application has been destroyed" not in str(e) and "can't invoke \"update\" command" not in str(e):
            raise

if __name__ == "__main__":
    asyncio.run(tkinter_async_loop())