"""Pruebas del handler de logging de la GUI.

Cubre la regresión concreta que se corrigió: al reconstruir la interfaz (cambio
de idioma) el widget destino queda destruido, y el handler debe desactivarse en
lugar de propagar TclError en cada registro.
"""

import logging
import tkinter as tk

from core.logging_handler import CustomTkinterLogHandler


class FakeWidget:
    """Doble de prueba de un CTkTextbox, sin dependencias de Tk."""

    def __init__(self, destroyed: bool = False) -> None:
        self.destroyed = destroyed
        self.inserted: list[str] = []

    def _check(self) -> None:
        if self.destroyed:
            raise tk.TclError('invalid command name ".!ctktextbox"')

    def configure(self, **kwargs) -> None:
        self._check()

    def insert(self, index: str, text: str) -> None:
        self._check()
        self.inserted.append(text)

    def see(self, index: str) -> None:
        self._check()

    def after(self, delay: int, func, *args) -> str:
        self._check()
        func(*args)
        return "after#0"


def _record(msg: str) -> logging.LogRecord:
    return logging.LogRecord("test", logging.INFO, __file__, 1, msg, None, None)


def test_escribe_en_el_widget() -> None:
    widget = FakeWidget()
    handler = CustomTkinterLogHandler(widget)

    handler.emit(_record("hola"))

    assert widget.inserted == ["hola\n"]


def test_widget_destruido_no_propaga_error() -> None:
    widget = FakeWidget(destroyed=True)
    handler = CustomTkinterLogHandler(widget)

    handler.emit(_record("mensaje tras destruir la UI"))  # no debe lanzar

    assert handler._disabled is True


def test_handler_desactivado_ignora_registros_posteriores() -> None:
    widget = FakeWidget()
    handler = CustomTkinterLogHandler(widget)
    handler.close()

    handler.emit(_record("descartado"))

    assert widget.inserted == []


def test_no_se_acumulan_handlers_en_el_logger_raiz() -> None:
    """Reproduce el ciclo de reconstrucción de UI del cambio de idioma."""
    root = logging.getLogger()
    previos = list(root.handlers)
    try:
        actual = None
        for _ in range(5):
            if actual is not None:
                root.removeHandler(actual)
                actual.close()
            actual = CustomTkinterLogHandler(FakeWidget())
            root.addHandler(actual)

        propios = [h for h in root.handlers if isinstance(h, CustomTkinterLogHandler)]
        assert len(propios) == 1
    finally:
        root.handlers = previos
