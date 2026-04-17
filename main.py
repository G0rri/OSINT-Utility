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
from customtkinter import filedialog

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

# Configuración global
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class OSINTApp(ctk.CTk):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop
        
        self.title("OSINT V2 - Panel Central Asíncrono")
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
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) 
        
        # --- HEADER PRINCIPAL ---
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        # Tabview para categorizar herramientas
        self.tabview = ctk.CTkTabview(self.header_frame, command=self._on_tab_change, height=80)
        self.tabview.grid(row=0, column=0, columnspan=5, padx=10, pady=(5, 10), sticky="ew")
        
        self.tabview.add("Identidades")
        self.tabview.add("Red")
        self.tabview.add("Forense")
        
        # Pestaña Identidades (Holehe, Sherlock)
        self.identidades_var = ctk.StringVar(value="Holehe")
        ctk.CTkRadioButton(self.tabview.tab("Identidades"), text="Holehe (Correo)", variable=self.identidades_var, value="Holehe", command=self._on_tool_change).pack(side="left", padx=20, pady=10)
        ctk.CTkRadioButton(self.tabview.tab("Identidades"), text="Sherlock (Username)", variable=self.identidades_var, value="Sherlock", command=self._on_tool_change).pack(side="left", padx=20, pady=10)
        ctk.CTkRadioButton(self.tabview.tab("Identidades"), text="PhoneInfoga (Teléfono)", variable=self.identidades_var, value="PhoneInfoga", command=self._on_tool_change).pack(side="left", padx=20, pady=10)
        
        # Pestaña Red (VirusTotal, WHOIS, Subdominios, Escáner de Puertos)
        self.red_var = ctk.StringVar(value="VirusTotal")
        ctk.CTkRadioButton(self.tabview.tab("Red"), text="VirusTotal", variable=self.red_var, value="VirusTotal", command=self._on_tool_change).pack(side="left", padx=10, pady=10)
        ctk.CTkRadioButton(self.tabview.tab("Red"), text="WHOIS/DNS", variable=self.red_var, value="WHOIS", command=self._on_tool_change).pack(side="left", padx=10, pady=10)
        ctk.CTkRadioButton(self.tabview.tab("Red"), text="Subdominios", variable=self.red_var, value="Subdominios", command=self._on_tool_change).pack(side="left", padx=10, pady=10)
        ctk.CTkRadioButton(self.tabview.tab("Red"), text="Puertos", variable=self.red_var, value="PortScanner", command=self._on_tool_change).pack(side="left", padx=10, pady=10)
        ctk.CTkRadioButton(self.tabview.tab("Red"), text="Cabeceras HTTP", variable=self.red_var, value="SecurityHeaders", command=self._on_tool_change).pack(side="left", padx=10, pady=10)
        
        # Pestaña Forense (Metadatos, Wayback Machine)
        self.forense_var = ctk.StringVar(value="Metadatos")
        ctk.CTkRadioButton(self.tabview.tab("Forense"), text="Metadatos (Imagen/PDF)", variable=self.forense_var, value="Metadatos", command=self._on_tool_change).pack(side="left", padx=20, pady=10)
        ctk.CTkRadioButton(self.tabview.tab("Forense"), text="Wayback Machine (URL/Dominio)", variable=self.forense_var, value="Wayback", command=self._on_tool_change).pack(side="left", padx=20, pady=10)

        # Contenedor Inferior del Header para Buscador (Barra Entry + Botones)
        self.search_bar_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.search_bar_frame.grid(row=1, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew")
        self.search_bar_frame.grid_columnconfigure(0, weight=1)

        self.target_entry = ctk.CTkEntry(
            self.search_bar_frame, 
            placeholder_text="Ingresa el correo (para Holehe)"
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
            text="Buscar", 
            command=self.run_tool_action
        )
        self.btn_search.grid(row=0, column=2, padx=(0, 10), pady=0)
        
        self.btn_stop = ctk.CTkButton(
            self.search_bar_frame, 
            text="Detener", 
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
            text="Limpiar Consola",
            fg_color="#8B0000",
            hover_color="#A52A2A",
            width=140,
            command=self.clear_console
        )
        self.btn_clear.grid(row=0, column=1, padx=(0, 10))
        
        self.btn_save = ctk.CTkButton(
            self.footer_frame,
            text="Guardar Reporte",
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
        self._on_tool_change()

    def _get_active_tool_name(self):
        current_tab = self.tabview.get()
        if current_tab == "Identidades":
            return self.identidades_var.get()
        elif current_tab == "Red":
            return self.red_var.get()
        elif current_tab == "Forense":
            return self.forense_var.get()
        return ""

    def _on_tool_change(self):
        choice = self._get_active_tool_name()
        
        # Mitigación para el bug de CustomTkinter donde el placeholder se vuelve texto editable
        def set_placeholder(text):
            current_val = self.target_entry.get()
            self.focus() # Quitar foco del entry temporalmente
            self.target_entry.configure(placeholder_text=text)
            if not current_val:
                self.target_entry.delete(0, "end")

        if choice == "Metadatos":
            self.btn_file.configure(state="normal")
            set_placeholder("Añade la ruta del archivo (o usa el botón 📂)")
        else:
            self.btn_file.configure(state="disabled")
            if choice == "Holehe":
                set_placeholder("Ingresa el correo (para Holehe)")
            elif choice == "Sherlock":
                set_placeholder("Ingresa el username (para Sherlock)")
            elif choice == "PhoneInfoga":
                set_placeholder("Ingresa el teléfono (ej: +34600123456)")
            elif choice == "VirusTotal":
                set_placeholder("Ingresa IP o Dominio (para VirusTotal)")
            elif choice == "WHOIS":
                set_placeholder("Ingresa el dominio (para WHOIS)")
            elif choice == "Subdominios":
                set_placeholder("Ingresa el dominio raíz (para Subdominios)")
            elif choice == "PortScanner":
                set_placeholder("Ingresa IP o Dominio (para Escáner de Puertos)")
            elif choice == "SecurityHeaders":
                set_placeholder("Ingresa URL o Dominio (para Cabeceras HTTP)")
            elif choice == "Wayback":
                set_placeholder("Ingresa URL o Dominio (para Wayback Machine)")

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
        
        # Resolving Active Module
        if selected_tool == "Holehe":
            active_module = self.holehe_module
        elif selected_tool == "Sherlock":
            active_module = self.sherlock_module
        elif selected_tool == "PhoneInfoga":
            active_module = self.phoneinfoga_module
        elif selected_tool == "VirusTotal":
            active_module = self.virustotal_module
        elif selected_tool == "WHOIS":
            active_module = self.whois_module
        elif selected_tool == "Subdominios":
            active_module = self.subdomain_module
        elif selected_tool == "PortScanner":
            active_module = self.port_scanner_module
        elif selected_tool == "SecurityHeaders":
            active_module = self.security_headers_module
        elif selected_tool == "Wayback":
            active_module = self.wayback_module
        elif selected_tool == "Metadatos":
            active_module = self.metadata_module
        else:
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
        self.destroy()

async def tkinter_async_loop():
    loop = asyncio.get_running_loop()
    app = OSINTApp(loop)
    try:
        while True:
            app.update()               
            await asyncio.sleep(0.01)
    except Exception as e:
        if "application has been destroyed" not in str(e) and "can't invoke \"update\" command" not in str(e):
            raise

if __name__ == "__main__":
    # La política por defecto desde Python 3.8 en Windows es ProactorEventLoop.
    # NO debemos usar WindowsSelectorEventLoopPolicy porque rompe el soporte
    # para subprocesos asíncronos (necesitado por módulos como PhoneInfoga).
    asyncio.run(tkinter_async_loop())