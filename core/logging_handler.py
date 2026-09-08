import logging
import threading
import tkinter as tk
from typing import Any


class CustomTkinterLogHandler(logging.Handler):
    """Redirige los logs de la aplicación a un widget de texto de CustomTkinter.

    El handler es tolerante a dos situaciones propias de una GUI:
      - El widget destino puede ser destruido (p. ej. al reconstruir la interfaz
        tras un cambio de idioma). En ese caso el handler se desactiva a sí mismo
        en lugar de propagar TclError en cada llamada a logging.
      - Tkinter no es thread-safe. Los registros emitidos desde hilos secundarios
        (los lanzados por `asyncio.to_thread`) se reencolan en el bucle de la GUI.
    """

    def __init__(self, text_widget: Any) -> None:
        super().__init__()
        self.text_widget: Any = text_widget
        self._owner_thread_id: int = threading.get_ident()
        self._disabled: bool = False

    def _append(self, msg: str) -> None:
        """Escribe en el widget. Solo debe invocarse desde el hilo de la GUI."""
        if self._disabled:
            return
        try:
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.configure(state="disabled")
            self.text_widget.see("end")
        except tk.TclError:
            # El widget ya no existe: desactivamos el handler de forma definitiva.
            self._disabled = True

    def emit(self, record: logging.LogRecord) -> None:
        if self._disabled:
            return

        msg: str = self.format(record)

        if threading.get_ident() == self._owner_thread_id:
            self._append(msg)
            return

        try:
            self.text_widget.after(0, self._append, msg)
        except (tk.TclError, RuntimeError):
            self._disabled = True

    def close(self) -> None:
        """Marca el handler como inservible antes de descartarlo."""
        self._disabled = True
        super().close()
