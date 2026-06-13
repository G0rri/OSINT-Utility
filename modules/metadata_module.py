import asyncio
import logging
import os
from typing import Any, Callable

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)

_PIL_AVAILABLE: bool = False
_PYPDF2_AVAILABLE: bool = False

# Inicialización preventiva global para eliminar advertencias "possibly unbound"
Image: Any = None
TAGS: dict[int, str] = {}
GPSTAGS: dict[int, str] = {}
PdfReader: Any = None

try:
    from PIL import Image
    from PIL.ExifTags import GPSTAGS, TAGS

    _PIL_AVAILABLE = True
except ImportError as import_err:
    logger.warning(
        "La librería Pillow (PIL) no está instalada en el entorno: %s", import_err
    )

try:
    from PyPDF2 import PdfReader

    _PYPDF2_AVAILABLE = True
except ImportError as import_err:
    logger.warning("La librería PyPDF2 no está instalada en el entorno: %s", import_err)


class MetadataModule(BaseModule):
    """Módulo nativo asíncrono para extracción forense de metadatos locales (Imágenes EXIF, PDF)."""

    def __init__(self) -> None:
        super().__init__("Metadatos")

    def check_health(self) -> tuple[str, str]:
        """Evalúa las dependencias del ecosistema forense local."""
        if _PIL_AVAILABLE and _PYPDF2_AVAILABLE:
            return "ok", "metadata_ok"
        if not _PIL_AVAILABLE and not _PYPDF2_AVAILABLE:
            return "error", "metadata_deps_missing"
        return "warning", "metadata_partial"

    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Aísla las lecturas de flujo binario de archivos locales en hilos seguros de procesamiento."""
        callback(f"[*] Analizando metadatos del archivo local: {target}\n")

        if not os.path.exists(target):
            callback(
                f"[-] Error crítico: El archivo '{target}' no existe o fue borrado.\n"
            )
            return {"status": "error", "error": "File not found"}

        ext: str = os.path.splitext(target)[1].lower()
        results: dict[str, Any] = {"target": target, "metadata": {}}

        try:
            # --- Clúster Fotográfico ---
            if ext in [".jpg", ".jpeg", ".png", ".tiff", ".webp"]:
                if not _PIL_AVAILABLE or Image is None:
                    callback(
                        "[-] Error: El módulo Pillow no está disponible en este entorno.\n"
                    )
                    return {"status": "error", "error": "Pillow unavailable"}

                callback("[*] Formato de imagen detectado. Leyendo clúster EXIF...\n")
                metadata: dict[str, Any] = await asyncio.to_thread(
                    self._extract_image_metadata, target
                )

                if not metadata:
                    callback(
                        "[-] No se encontraron metadatos EXIF útiles en esta imagen.\n"
                    )
                else:
                    callback("[+] Metadatos de Imagen extraídos:\n")
                    for k, v in metadata.items():
                        if k == "GPSInfo" and isinstance(v, dict):
                            callback(
                                "    - 🌍 DATOS GPS (Geolocalización detectada):\n"
                            )
                            for gk, gv in v.items():
                                callback(f"       • {gk}: {gv}\n")
                        else:
                            callback(f"    - 📷 {k}: {v}\n")

                results["metadata"] = metadata

            # --- Clúster PDF Documental ---
            elif ext == ".pdf":
                if not _PYPDF2_AVAILABLE or PdfReader is None:
                    callback(
                        "[-] Error: El módulo PyPDF2 no está disponible en este entorno.\n"
                    )
                    return {"status": "error", "error": "PyPDF2 unavailable"}

                callback(
                    "[*] Formato PDF detectado. Leyendo Diccionario de Propiedades...\n"
                )
                metadata = await asyncio.to_thread(self._extract_pdf_metadata, target)

                if not metadata:
                    callback(
                        "[-] El PDF está encriptado o no cuenta con metadatos legibles.\n"
                    )
                else:
                    callback("[+] Metadatos Estructurales PDF extraídos:\n")
                    for k, v in metadata.items():
                        callback(f"    - 📄 {k}: {v}\n")

                results["metadata"] = metadata

            else:
                callback(
                    f"[-] Análisis profundo no soportado para la extensión: {ext}\n"
                )
                stat: os.stat_result = await asyncio.to_thread(os.stat, target)
                callback("[+] Información Base del Sistema Operativo:\n")
                callback(f"    - Peso en bytes: {stat.st_size}\n")
                results["metadata"] = {"size": stat.st_size}

        except OSError as err:
            logger.error(
                "Error de Entrada/Salida en el acceso al archivo forense: %s", err
            )
            callback(f"[-] Error de sistema al abrir el archivo: {err}\n")
            return {"status": "error", "error": str(err)}
        except ValueError as err:
            logger.error(
                "Error de consistencia estructural en el archivo analizado: %s", err
            )
            callback(f"[-] Estructura de archivo corrupta o inválida: {err}\n")
            return {"status": "error", "error": str(err)}

        callback("\n[+] Módulo forense finalizado con éxito.\n")
        results["status"] = "success"
        return results

    def _extract_image_metadata(self, filepath: str) -> dict[str, Any]:
        """Extrae de forma síncrona el EXIF mapeando las etiquetas de geolocalización."""
        metadata: dict[str, Any] = {}
        if not _PIL_AVAILABLE or Image is None:
            return metadata

        with Image.open(filepath) as img:
            # Usamos getattr para evitar advertencias de stubs estrictos sobre atributos internos
            _getexif_func = getattr(img, "_getexif", None)
            exif_data: Any = _getexif_func() if _getexif_func else None
            if not exif_data:
                return metadata

            for tag_id, value in exif_data.items():
                tag: str = TAGS.get(tag_id, str(tag_id))

                if tag == "GPSInfo":
                    gps_data: dict[str, Any] = {}
                    for t in value:
                        sub_tag: str = GPSTAGS.get(t, str(t))
                        gps_data[sub_tag] = value[t]
                    metadata[tag] = gps_data
                else:
                    if isinstance(value, bytes):
                        if len(value) > 200:
                            continue
                        try:
                            value = value.decode("utf-8", errors="replace")
                        except (UnicodeDecodeError, AttributeError) as err:
                            logger.debug(
                                "No se pudo decodificar el tag EXIF binario %s, fallback a string: %s",
                                tag,
                                err,
                            )
                            value = str(value)
                    metadata[tag] = value

        important_keys: list[str] = [
            "Make",
            "Model",
            "Software",
            "DateTime",
            "DateTimeOriginal",
            "GPSInfo",
        ]
        filtered_metadata: dict[str, Any] = {
            k: v for k, v in metadata.items() if k in important_keys
        }

        return filtered_metadata if filtered_metadata else metadata

    def _extract_pdf_metadata(self, filepath: str) -> dict[str, Any]:
        """Efectúa la lectura forense del diccionario binario estructural /Info del PDF."""
        metadata: dict[str, Any] = {}
        if not _PYPDF2_AVAILABLE or PdfReader is None:
            return metadata

        with open(filepath, "rb") as f:
            reader = PdfReader(f)
            info: Any = reader.metadata
            if not info:
                return metadata

            for key, value in info.items():
                if value:
                    clean_key: str = key.strip("/")
                    metadata[clean_key] = str(value)

        return metadata
