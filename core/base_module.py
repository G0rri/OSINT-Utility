from abc import ABC, abstractmethod
from typing import Any, Callable

class BaseModule(ABC):
    """
    Clase base abstracta para todos los módulos de OSINT V2.
    Define el contrato estricto de concurrencia y callbacks visuales.
    """
    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    async def run(self, target: str, callback: Callable[[str], None]) -> dict[str, Any]:
        """
        Ejecuta el módulo de forma asíncrona.
        
        :param target: El objetivo a investigar (ej. email, username, ip).
        :param callback: Función a llamar para reportar progreso a la interfaz en tiempo real.
                         Debe ser segura para llamar múltiples veces e insertar texto/estados.
        :return: Diccionario con los resultados estructurados de la ejecución para telemetría
                 o almacenamiento futuro en base de datos.
        """
        pass
