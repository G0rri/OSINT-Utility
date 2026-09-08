"""Despachador de las tareas asíncronas de los módulos."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from core.base_module import BaseModule

logger: logging.Logger = logging.getLogger(__name__)


class TaskRunner:
    """Lanza y cancela la ejecución de un módulo, notificando inicio y fin.

    Solo admite una tarea simultánea, igual que la interfaz: mientras hay un
    módulo en marcha los controles de búsqueda permanecen bloqueados.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        write: Callable[[str], None],
        on_start: Callable[[], None],
        on_finish: Callable[[], None],
    ) -> None:
        self._loop: asyncio.AbstractEventLoop = loop
        self._write: Callable[[str], None] = write
        self._on_start: Callable[[], None] = on_start
        self._on_finish: Callable[[], None] = on_finish
        self._task: asyncio.Task[Any] | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self, module: BaseModule, target: str) -> None:
        """Programa la ejecución del módulo sobre el objetivo indicado."""
        if self.is_running:
            logger.warning("Ya hay una tarea en curso; se ignora la nueva petición.")
            return

        self._on_start()
        self._task = self._loop.create_task(self._execute(module, target))

    def cancel(self) -> None:
        """Solicita la cancelación de la tarea en curso, si la hay."""
        if self.is_running and self._task is not None:
            self._task.cancel()

    async def _execute(self, module: BaseModule, target: str) -> None:
        try:
            await module.run(target, self._write)
        except asyncio.CancelledError:
            self._write("\n[!] Tarea cancelada por el usuario.\n")
        except (RuntimeError, ValueError, OSError) as err:
            logger.error("Error de ejecución en %s: %s", module.name, err)
            self._write(f"\n[!] Error de ejecución en {module.name}: {err}\n")
        finally:
            self._task = None
            self._on_finish()
