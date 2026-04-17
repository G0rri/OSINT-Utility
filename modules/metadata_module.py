import asyncio
import os
from core.base_module import BaseModule

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    pass

try:
    from PyPDF2 import PdfReader
except ImportError:
    pass

class MetadataModule(BaseModule):
    """
    Módulo nativo asíncrono para extracción forense de metadatos locales (Imágenes EXIF, PDF).
    """
    async def run(self, target: str, callback) -> dict:
        callback(f"[*] Analizando metadatos del archivo local: {target}\n")
        
        # Validador rápido (aunque main.py debe filtrarlo antes)
        if not os.path.exists(target):
            callback(f"[-] Error crítico: El archivo '{target}' no existe o fue borrado.\n")
            return {"status": "error", "error": "File not found"}
            
        ext = os.path.splitext(target)[1].lower()
        results = {"target": target, "metadata": {}}
        
        try:
            # Archivos Fotográficos
            if ext in ['.jpg', '.jpeg', '.png', '.tiff', '.webp']:
                callback("[*] Formato de imagen detectado. Leyendo clúster EXIF...\n")
                
                # Las operaciones I/O en discos HDD/SSD grandes pueden bloquear el procesador.
                # Delegamos la extracción de PIL al threadpool seguro de asyncio:
                metadata = await asyncio.to_thread(self._extract_image_metadata, target)
                
                if not metadata:
                    callback("[-] No se encontraron metadatos EXIF útiles en esta imagen.\n")
                else:
                    callback("[+] Metadatos de Imagen extraídos:\n")
                    for k, v in metadata.items():
                        if k == "GPSInfo" and isinstance(v, dict):
                            callback("    - 🌍 DATOS GPS (Geolocalización detectada):\n")
                            for gk, gv in v.items():
                                callback(f"       • {gk}: {gv}\n")
                        else:
                            callback(f"    - 📷 {k}: {v}\n")
                
                results["metadata"] = metadata
                
            # Archivos PDF Documentales
            elif ext == '.pdf':
                callback("[*] Formato PDF detectado. Leyendo Diccionario de Propiedades...\n")
                metadata = await asyncio.to_thread(self._extract_pdf_metadata, target)
                
                if not metadata:
                    callback("[-] El PDF está encriptado o no cuenta con metadatos legibles.\n")
                else:
                    callback("[+] Metadatos Estructurales PDF extraídos:\n")
                    for k, v in metadata.items():
                        callback(f"    - 📄 {k}: {v}\n")
                        
                results["metadata"] = metadata
                
            else:
                callback(f"[-] Análisis profundo no soportado para la extensión: {ext}\n")
                stat = await asyncio.to_thread(os.stat, target)
                callback(f"[+] Información Base del Sistema Operativo:\n")
                callback(f"    - Peso en bytes: {stat.st_size}\n")
                results["metadata"] = {"size": stat.st_size}
                
        except Exception as e:
            callback(f"[-] Error grave analizando la estructura del archivo: {e}\n")
            return {"status": "error", "error": str(e)}

        callback("\n[+] Módulo forense finalizado con éxito.\n")
        results["status"] = "success"
        return results

    def _extract_image_metadata(self, filepath: str) -> dict:
        """Extrae el EXIF de las imágenes y mapea los diccionarios de GPS (Llamada Bloqueante)"""
        metadata = {}
        with Image.open(filepath) as img:
            # Validamos si es capaz de extraer diccionario _getexif() de PIL
            exif_data = img._getexif() if hasattr(img, '_getexif') else None
            if not exif_data:
                return metadata
                
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                
                # Desentramar y decodificar bloque especifico de Coordenadas de Satélite
                if tag == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_tag = GPSTAGS.get(t, t)
                        gps_data[sub_tag] = value[t]
                    metadata[tag] = gps_data
                else:
                    # Filtramos bloques bytes brutos kilometricos irrelevantes que crashearian el string
                    if isinstance(value, bytes):
                        if len(value) > 200:
                            continue
                        try:
                            value = value.decode('utf-8', errors='replace')
                        except:
                            value = str(value)
                    metadata[tag] = value
        
        # Preferimos aislar la telemetría mas útil en OSINT
        important_keys = ["Make", "Model", "Software", "DateTime", "DateTimeOriginal", "GPSInfo"]
        filtered_metadata = {k: v for k, v in metadata.items() if k in important_keys}
        
        return filtered_metadata if filtered_metadata else metadata

    def _extract_pdf_metadata(self, filepath: str) -> dict:
        """Extrae metadatos documentales desde la cola binaria de PDFs (Llamada Bloqueante)"""
        metadata = {}
        with open(filepath, 'rb') as f:
            reader = PdfReader(f)
            # metadata property extrae la etiqueta /Info (DocumentInformation)
            info = reader.metadata
            if not info:
                return metadata
                
            for key, value in info.items():
                if value:
                    clean_key = key.strip('/')
                    metadata[clean_key] = value
                
        return metadata
