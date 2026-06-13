import logging
from typing import Any


class CustomTkinterLogHandler(logging.Handler):
    """Redirige los logs de la aplicación a un widget de texto de CustomTkinter."""

    def __init__(self, text_widget: Any) -> None:
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        msg: str = self.format(record)
        # Inserción segura en el widget de la GUI
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", msg + "\n")
        self.text_widget.configure(state="disabled")
        self.text_widget.see("end")
