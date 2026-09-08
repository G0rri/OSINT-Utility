"""Configuración compartida de la batería de pruebas.

Las pruebas no realizan ninguna petición de red real: todo tráfico HTTP se
sustituye por transportes simulados de httpx.
"""

import os
import sys

# Permite importar `core` y `modules` sin instalar el proyecto como paquete.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
