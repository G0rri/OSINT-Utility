# OSINT Utility V2 🕵️‍♂️🔍

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet)
![Asyncio](https://img.shields.io/badge/Asyncio-Enabled-green)
![Linux](https://img.shields.io/badge/Platform-Linux-orange)
![i18n](https://img.shields.io/badge/i18n-ES%20%7C%20EN-yellow)

**OSINT Utility V2** es una potente y moderna aplicación de escritorio desarrollada en Python. Diseñada para investigadores, analistas de ciberseguridad o entusiastas del OSINT (Inteligencia de Fuentes Abiertas), la aplicación ofrece una interfaz centralizada y fácil de usar para ejecutar múltiples herramientas de recolección de información sin necesidad de abrir la terminal.

Gracias a su arquitectura asíncrona basada en `asyncio` y su interfaz gráfica construida con `CustomTkinter`, permite realizar análisis complejos en segundo plano, manteniendo la fluidez y respuesta de la interfaz.

---

## 🚀 Características Principales

- **Interfaz Gráfica Moderna (GUI):** Olvídate de recordar comandos. Todo se gestiona mediante una interfaz limpia y oscura.
- **Ejecución Asíncrona Aislada:** Realiza búsquedas complejas mediante subprocesos nativos que no bloquean la interfaz de usuario. Tienes control total para cancelar escaneos en milisegundos y de manera limpia, sin dejar procesos "zombies" en tu sistema.
- **Arquitectura Modular:** Diseñada mediante módulos (plugins), lo que facilita agregar o modificar herramientas de investigación.
- **Indicadores de Salud en Tiempo Real:** Cada herramienta muestra un indicador visual (🟢 listo / 🟠 parcial / 🔴 error) que comprueba si sus dependencias y claves de API están configuradas correctamente, con tooltips explicativos al pasar el ratón.
- **Internacionalización (i18n):** Interfaz disponible en **Español** e **Inglés**, cambiable en caliente desde la barra superior.
- **Exportación de Resultados:** Guarda cualquier resultado generado en la consola como un informe `.txt` con un solo clic.
- **Todo en Uno:** Agrupa herramientas populares de OSINT en un solo panel de control.

---

## 🛠️ Módulos y Herramientas Integradas

La aplicación se divide en las siguientes áreas de inteligencia:

### 🌐 Red
- **WHOIS & DNS:** Obtiene información de registro de dominios y enumera los registros DNS más importantes (A, MX, TXT, etc.).
- **Escáner de Puertos:** Comprueba los puertos lógicos de un host o IP usando la base de datos de Shodan (InternetDB, sin cuenta necesaria).
- **Enumeración de Subdominios:** Encuentra subdominios asociados a un dominio principal usando crt.sh y HackerTarget como fuentes. Genera automáticamente un **grafo interactivo de red** en el navegador para visualizar las relaciones entre el dominio raíz y sus subdominios.

### 🛡️ Análisis Web
- **Wayback Machine:** Recupera el historial de un sitio web, permitiéndote investigar cómo era o qué contenía antes de ser modificado.
- **Cabeceras de Seguridad HTTP:** Analiza los *Security Headers* implementados en un sitio y detecta configuraciones faltantes o vulnerables (HSTS, CSP, X-Frame-Options, etc.).
- **VirusTotal:** Consulta la reputación de dominios e IPs contra los motores de análisis de la plataforma líder del mercado (requiere API Key).

### 👤 Identidades
- **Sherlock:** Rastrea un nombre de usuario a través de cientos de foros y redes sociales.
- **Holehe:** Comprueba un correo electrónico contra múltiples sitios web basándose en funciones de recuperación de contraseñas.
- **PhoneInfoga:** Escanea números de teléfono a nivel mundial para obtener su formato, operador y tipo de línea.

### 📄 Forense Local
- **Lector de Metadatos:** Extrae información EXIF oculta de imágenes (JPG, PNG, TIFF, WEBP) y documentos PDF: nombre del creador, modelo de cámara, coordenadas GPS, fechas, software utilizado, etc.

---

## ⚙️ Instalación y Configuración

El proyecto está diseñado para funcionar nativamente en entornos **Linux** de la forma más sencilla posible.

### 1. Requisitos del sistema

Asegúrate de tener instalada la librería `tk` nativa:

- **Arch Linux / CachyOS:** `sudo pacman -S tk`
- **Ubuntu / Debian:** `sudo apt install python3-tk`

### 2. Clonar el repositorio

```bash
git clone https://github.com/G0rri/OSINT-Utility.git
cd OSINT-Utility
```

### 3. Configurar las claves de API

Renombra el archivo `.env.example` a `.env` y rellena tus claves reales:

```bash
cp .env.example .env
```

| Variable | Módulo | Obligatoria |
|---|---|---|
| `VIRUSTOTAL_API_KEY` | VirusTotal | Sí (el módulo no funciona sin ella) |
| `NUMVERIFY_API_KEY` | PhoneInfoga | No (mejora los resultados) |
| `APILAYER_KEY` | PhoneInfoga | No (mejora los resultados) |

### 4. Ejecutar

```bash
chmod +x start.sh
./start.sh
```

El script creará el entorno virtual (`venv`), instalará todas las dependencias Python, descargará automáticamente el binario de PhoneInfoga para Linux si no está presente y lanzará la aplicación.

---

## 🏗️ Tecnología Utilizada

- **Python 3.10+** — Lógica principal de la aplicación.
- **CustomTkinter** — Diseño y estética de la interfaz.
- **Asyncio** — Ejecución asíncrona de módulos sin congelaciones de UI.
- **httpx** — Cliente HTTP asíncrono para peticiones a APIs externas.
- **pyvis** — Generación de grafos interactivos HTML para subdominios.
- **Librerías OSINT:** `sherlock-project`, `holehe`, `python-whois`, `dnspython`, `Pillow`, `PyPDF2`.

---

## ⚠️ Aviso Legal / Disclaimer

**Solo para uso ético.** El uso de OSINT Utility para investigar objetivos sin su previo consentimiento podría ser ilegal en tu país. El creador y responsables del repositorio no asumen ninguna responsabilidad en caso de uso indebido o daño derivado de este software.

¡Disfruta recolectando conocimiento! 🕵️‍♀️
