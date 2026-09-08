"""Arranque del entorno: carga del .env y validación pasiva de las claves.

Se mantiene separado de la interfaz para que las pruebas y cualquier futuro
frontend (CLI, por ejemplo) puedan inicializar el entorno sin importar Tkinter.
"""

import logging
import os

logger: logging.Logger = logging.getLogger(__name__)

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH: str = os.path.join(PROJECT_ROOT, ".env")

# Valor de la plantilla .env.example: si sigue ahí, la clave no está configurada.
_PLACEHOLDER: str = "tu_api_key_aqui"


def is_configured(value: str | None) -> bool:
    """Indica si una variable de entorno contiene una clave real."""
    return bool(value and value.strip() and value.strip().lower() != _PLACEHOLDER)


def load_environment() -> None:
    """Carga el .env de la raíz del proyecto mediante una ruta absoluta."""
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=ENV_PATH)


def validar_entorno() -> None:
    """Avisa de las claves ausentes sin impedir el arranque de la aplicación.

    Los módulos afectados quedarán en estado de alerta (🟠/🔴), pero el resto
    de la suite es plenamente funcional.
    """
    if not is_configured(os.getenv("VIRUSTOTAL_API_KEY")):
        logging.warning(
            "Aviso: VIRUSTOTAL_API_KEY no configurada en el .env. "
            "La aplicación iniciará, pero el módulo de VirusTotal mostrará "
            "un estado de alerta."
        )


def bootstrap_environment() -> None:
    """Punto de entrada único: carga el entorno y ejecuta la validación pasiva."""
    load_environment()
    validar_entorno()
