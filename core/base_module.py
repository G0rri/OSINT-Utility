# core/base_module.py
from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseModule(ABC):
    """Interfaz abstracta obligatoria para todos los módulos OSINT."""

    def __init__(self, name: str, language: str = "es") -> None:
        self.name: str = name
        self.language: str = language

    @abstractmethod
    def check_health(self) -> tuple[str, str]:
        """Verifica dependencias y claves. Retorna un tuple[estado, clave_msg]."""
        pass

    @abstractmethod
    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """Ejecuta la lógica principal del módulo de forma asíncrona."""
        pass
