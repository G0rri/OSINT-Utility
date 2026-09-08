# OSINT-Utility V2 🕵️‍♂️

Suite OSINT modular y asíncrona construida con Python 3.10+ y una interfaz
gráfica basada en CustomTkinter. Integra 10 módulos de recolección bajo una
arquitectura de plugins común.

---

## 🏗️ Arquitectura

- **Núcleo asíncrono (`asyncio`).** Las peticiones de red y los subprocesos
  pesados se ejecutan como tareas concurrentes, de modo que la GUI nunca se
  bloquea. Las llamadas bloqueantes inevitables (`whois`, `socket.gethostbyname`,
  lectura EXIF/PDF) se delegan a `asyncio.to_thread`.
- **Arquitectura de plugins (`BaseModule`).** Todos los módulos heredan de una
  clase base abstracta que impone el mismo contrato: `check_health()` para el
  diagnóstico previo y `run(target, callback)` para la ejecución.
- **Catálogo declarativo (`core/registry.py`).** La interfaz se construye a
  partir de una tabla de `ToolSpec`. Dar de alta un módulo es añadir una entrada
  con su categoría, sus claves de traducción y su fábrica; no hay que tocar la
  interfaz.
- **Subprocesos sin `shell=True`.** Los binarios externos (Sherlock,
  PhoneInfoga) se invocan mediante `asyncio.create_subprocess_exec` pasando los
  argumentos como lista. No hay superficie de inyección de comandos.
- **Manejo de errores específico.** No se usa `except Exception` en ninguna
  parte del código: cada módulo captura las excepciones concretas que puede
  producir (`httpx.HTTPStatusError`, `httpx.TimeoutException`, `socket.gaierror`,
  `dns.resolver.NXDOMAIN`…), de forma que un endpoint caído no tumba la sesión.
- **Logging nativo.** Sin `print()`. Un handler propio (`CustomTkinterLogHandler`)
  redirige los registros a la consola de la GUI; es tolerante a la destrucción
  del widget y reencola en el hilo de la interfaz los registros que llegan desde
  hilos secundarios.

---

## 🛠️ Módulos

| Categoría        | Módulo         | Objetivo             | Descripción                                                            |
| :--------------- | :------------- | :------------------- | :--------------------------------------------------------------------- |
| **Identidades**  | `Holehe`       | Email                | Rastrea el registro de un correo en cientos de sitios.                 |
|                  | `Sherlock`     | Username             | Correlaciona cuentas de redes sociales y foros por handle.             |
|                  | `PhoneInfoga`  | Teléfono             | Escáner de números apoyado en APIs externas.                           |
| **Red y Web**    | `VirusTotal`   | Reputación           | Consulta pasiva a la API v3 de VirusTotal para IPs y dominios.         |
|                  | `WHOIS / DNS`  | Registros de dominio | Resolución asíncrona de A, MX y TXT junto a los datos del registrador. |
|                  | `Subdominios`  | Infraestructura      | Descubrimiento vía crt.sh y HackerTarget, con grafo interactivo.       |
|                  | `Port Scanner` | Mapeo pasivo         | Puertos expuestos según Shodan InternetDB (sin enviar tráfico).        |
|                  | `Cabeceras`    | Hardening HTTP       | Evalúa HSTS, CSP, X-Frame-Options y X-Content-Type-Options.            |
|                  | `Wayback`      | Línea temporal       | Localiza la captura más antigua en Archive.org.                        |
| **Forense**      | `Metadatos`    | Ficheros locales     | Extracción de EXIF/GPS en imágenes y del diccionario /Info en PDF.     |

---

## 🚀 Instalación

### Requisitos

- Linux (Ubuntu/Debian/Arch/Fedora)
- Python 3.10 o superior

### Puesta en marcha

```bash
git clone https://github.com/G0rri/OSINT-Utility.git
cd OSINT-Utility
chmod +x start.sh
./start.sh
```

`start.sh` crea el entorno virtual, instala las dependencias fijadas en
`requirements.txt`, copia `.env.example` a `.env` si aún no existe y lanza la
aplicación.

### PhoneInfoga (opcional)

El script **no descarga ni ejecuta scripts remotos automáticamente**. Si quieres
usar el módulo de teléfonos, instala el binario tú mismo desde las releases
oficiales:

<https://github.com/sundowndev/phoneinfoga/releases>

Coloca el ejecutable `phoneinfoga` en la raíz del proyecto. `start.sh` le dará
permisos de ejecución en el siguiente arranque. Los otros 9 módulos funcionan con
normalidad sin él.

---

## 🔑 Claves de API

Todas son opcionales. Copia `.env.example` a `.env` y rellena las que quieras:

```ini
# Reputación de IPs y dominios
VIRUSTOTAL_API_KEY=tu_api_key_aqui

# Enriquecimiento de PhoneInfoga
NUMVERIFY_API_KEY=tu_api_key_aqui
APILAYER_KEY=tu_api_key_aqui
```

Si faltan, la aplicación arranca igualmente y marca los módulos afectados con un
semáforo 🟠/🔴; pasa el ratón por encima para ver el motivo.

---

## 🔒 Nota sobre TLS

El módulo de cabeceras **verifica los certificados TLS por defecto**. Un
certificado caducado, autofirmado o con la cadena rota se reporta como hallazgo
de la auditoría, no como un error de red. Si necesitas auditar igualmente un host
en ese estado (típico en preproducción), activa la casilla *«Ignorar errores de
certificado TLS»* de forma explícita.

---

## 📂 Estructura

```
main.py                  Punto de entrada: bootstrap + bucle asyncio/Tkinter
core/
  base_module.py         Contrato abstracto de los módulos
  config.py              Carga del .env y validación pasiva de claves
  registry.py            Catálogo declarativo de herramientas y categorías
  i18n.py                Traductor ES/EN
  logging_handler.py     Puente entre logging y la consola de la GUI
  visualizer.py          Grafos interactivos de subdominios
modules/                 Los 10 módulos OSINT, uno por fichero
ui/
  app.py                 Ventana principal: ensambla y coordina
  toolbar.py             Pestañas, semáforos de estado y casillas de opción
  console.py             Consola de salida: colores, enlaces y exportación
  runner.py              Despachador de las tareas asíncronas
  tooltip.py             Tooltips flotantes
tests/                   Batería de pruebas (sin red real)
```

### Añadir un módulo nuevo

1. Crea `modules/mi_modulo.py` heredando de `BaseModule` e implementa
   `check_health()` y `run()`.
2. Añade sus textos a `locales/es.json` y `locales/en.json`.
3. Añade una entrada `ToolSpec` en `core/registry.py`.

La interfaz, el placeholder, el semáforo de estado y el despacho de la tarea se
generan solos. `tests/test_registry.py` verifica que la entrada es coherente.

---

## 🧪 Desarrollo

```bash
./venv/bin/python3 -m pip install -r requirements-dev.txt
./venv/bin/python3 -m pytest        # batería de pruebas (sin red real)
./venv/bin/python3 -m ruff check .  # linter
./venv/bin/python3 -m ruff format . # formateo
```

Las pruebas de red usan `httpx.MockTransport`: no se realiza ninguna petición
real. `tests/test_registry.py` valida que cada entrada del catálogo apunte a
claves de traducción existentes y a métodos que el módulo implementa. La configuración de `ruff` y `pytest` vive en `pyproject.toml`.

Las versiones de `holehe` y `sherlock-project` están **fijadas a propósito**: sus
módulos parsean el stdout de esas herramientas, y un cambio de formato al
actualizar rompería el análisis de forma silenciosa.

---

## ⚠️ Aviso de uso ético

Esta herramienta está destinada exclusivamente a pruebas de seguridad
autorizadas, fines educativos e investigación defensiva. Usarla para recopilar
información sobre terceros sin su consentimiento previo y explícito puede
vulnerar la normativa de protección de datos o la legislación sobre delitos
informáticos según tu jurisdicción. El autor y los contribuidores declinan toda
responsabilidad por un uso indebido.
