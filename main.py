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