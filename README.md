# OSINT Utility V2 🕵️‍♂️🔍

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet)
![Asyncio](https://img.shields.io/badge/Asyncio-Enabled-green)

**OSINT Utility V2** es una potente y moderna aplicación de escritorio desarrollada en Python. Diseñada para investigadores, analistas de ciberseguridad o entusiastas del OSINT (Inteligencia de Fuentes Abiertas), la aplicación ofrece una interfaz centralizada y fácil de usar para ejecutar múltiples herramientas de recolección de información sin necesidad de abrir la terminal.

Gracias a su arquitectura asíncrona basada en `asyncio` y su interfaz gráfica construida con `CustomTkinter`, permite realizar análisis complejos en segundo plano, manteniendo la fluidez y respuesta de la interfaz.

---

## 🚀 Características Principales

- **Interfaz Gráfica Moderna (GUI):** Olvídate de recordar comandos. Todo se gestiona mediante una interfaz limpia y oscura.
- **Ejecución Asíncrona:** Realiza búsquedas sin bloquear la interfaz de usuario.
- **Arquitectura Modular:** Diseñada mediante módulos (plugins), lo que facilita agregar o modificar herramientas de investigación.
- **Todo en Uno:** Agrupa herramientas populares de OSINT en un solo panel de control.
- **Exportación de Resultados:** (En constante desarrollo) Facilidad para visualizar las cargas de respuesta de cada análisis.

---

## 🛠️ Módulos y Herramientas Integradas

La aplicación se divide en las siguientes áreas de inteligencia:

### 🌐 Dominio y Red
- **WHOIS & DNS:** Obtiene información de registro de dominios y enumera los registros DNS más importantes (A, MX, TXT, etc.).
- **Escáner de Puertos:** Comprueba los puertos lógicos de un host o IP para identificar servicios expuestos a internet.
- **Enumeración de Subdominios:** Encuentra subdominios asociados a un dominio principal utilizando diferentes fuentes (es ideal para expandir la superficie de ataque o reconocimiento).

### 🛡️ Análisis Web
- **Wayback Machine:** Recupera el historial de un sitio web, permitiéndote investigar cómo era o qué contenía antes de ser modificado.
- **Cabeceras de Seguridad y HTTP:** Analiza los *Security Headers* implementados en un sitio y busca configuraciones faltantes o vulnerables.
- **VirusTotal:** Consulta la API (o reputación) de dominios, IPs o hashes maliciosos para ver si están marcados como amenazas en la plataforma líder del mercado.

### 👤 Investigación de Identidades (Personas)
- **Sherlock:** Rastrea un nombre de usuario (username) a través de cientos de foros y redes sociales y detecta si dicho usuario existe en ellas.
- **Holehe:** Comprueba un correo electrónico contra múltiples sitios web (Twitter, Instagram, Imgur, etc.) basándose en funciones de recuperación para validar si la cuenta de correo está registrada.

### 📄 Análisis Forense Local
- **Lector de Metadatos:** Extrae información oculta o EXIF de ficheros, imágenes o documentos (por ejemplo, PDFs), ayudando a recolectar nombres de creadores, marcas de cámara, fechas, etc.

---

## ⚙️ Instalación y Configuración

Sigue estos pasos para ejecutar la aplicación en tu entorno local:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/OSINT-Utility.git
   cd OSINT-Utility
   ```

2. **Crear e iniciar el entorno virtual (Recomendado):**
   ```bash
   # En Windows
   python -m venv venv
   .\venv\Scripts\activate

   # En Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar los requisitos:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la herramienta:**
   ```bash
   python main.py
   ```

*(Nota: Asegúrate de comprobar si alguna de las herramientas como VirusTotal requiere que integres una API-KEY válida en la configuración de la propia herramienta o variables de entorno).*

---

## 🏗️ Tecnología Utilizada

- **Python** (Lógica principal de la aplicación).
- **CustomTkinter** (Para el diseño y estética de las ventanas, pestañas e inputs).
- **Asyncio / Threading** (Gestión de peticiones y subprocesos simultáneos sin congelaciones de UI).
- **Librerías principales:** `sherlock-project`, `holehe`, `python-whois`, `dnspython`, `httpx` (Ver *requirements.txt*).

---

## ⚠️ Aviso Legal / Disclaimer

**Solo para uso ético.** El uso de OSINT Utility para investigar objetivos sin su previo consentimiento podría ser ilegal en tu país. El creador y responsables del repositorio no asumen ninguna responsabilidad en caso del uso indebido o daño derivado de este software.

¡Disfruta recolectando conocimiento! 🕵️‍♀️
