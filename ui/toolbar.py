"""Selector de herramientas: pestañas, semáforos de estado y casillas de opción.

Se construye íntegramente a partir del catálogo `core.registry`, de modo que
añadir una herramienta nueva no requiere tocar este fichero.
"""

import logging
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from core.i18n import Translator
from core.registry import CATEGORIES, ToolRegistry, ToolSpec
from ui import tooltip

logger: logging.Logger = logging.getLogger(__name__)

# Estado devuelto por check_health -> (emoji, color del texto).
_HEALTH_STYLE: dict[str, tuple[str, str | None]] = {
    "ok": (" 🟢", "#4CAF50"),
    "warning": (" 🟠", "#FFA500"),
    "error": (" 🔴", "#F44336"),
}


class ToolSelector(ctk.CTkTabview):
    """Pestañas de categorías con un radio button por herramienta."""

    def __init__(
        self,
        master: Any,
        registry: ToolRegistry,
        translator: Translator,
        option_vars: dict[str, ctk.BooleanVar],
        on_change: Callable[[], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(master, command=self._handle_tab_change, **kwargs)

        self._registry: ToolRegistry = registry
        self._translator: Translator = translator
        self._on_change: Callable[[], None] = on_change

        # Las casillas de opción las posee la aplicación: así su valor sobrevive
        # a la reconstrucción de la interfaz al cambiar de idioma.
        self._option_vars: dict[str, ctk.BooleanVar] = option_vars

        self._selection: dict[str, ctk.StringVar] = {}
        self._tab_to_category: dict[str, str] = {}
        self._option_widgets: dict[str, ctk.CTkCheckBox] = {}

        self._build()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _build(self) -> None:
        for category in CATEGORIES:
            tab_name: str = self._translator.get(category.label_key)
            self.add(tab_name)
            self._tab_to_category[tab_name] = category.key

            self._selection[category.key] = ctk.StringVar(
                value=self._registry.default_for(category.key)
            )

            for spec in self._registry.specs_for(category.key):
                self._add_tool_radio(tab_name, spec, category.padx)
                if spec.option is not None:
                    self._add_option_checkbox(tab_name, spec)

    def _add_tool_radio(self, tab_name: str, spec: ToolSpec, padx: int) -> None:
        module = self._registry.module(spec.key)
        if module is None:
            logger.error("La herramienta '%s' no tiene módulo asociado.", spec.key)
            return

        status, msg_key = module.check_health()
        emoji, text_color = _HEALTH_STYLE.get(status, ("", None))
        msg: str = self._translator.get(msg_key) if msg_key else ""

        radio: ctk.CTkRadioButton = ctk.CTkRadioButton(
            self.tab(tab_name),
            text=self._translator.get(spec.label_key) + emoji,
            variable=self._selection[spec.category],
            value=spec.key,
            command=self._on_change,
        )
        if text_color:
            radio.configure(text_color=text_color)
        radio.pack(side="left", padx=padx, pady=10)

        tooltip.attach(radio, msg)

    def _add_option_checkbox(self, tab_name: str, spec: ToolSpec) -> None:
        """Crea la casilla asociada a una herramienta (oculta hasta seleccionarla)."""
        option = spec.option
        if option is None:
            return

        var: ctk.BooleanVar | None = self._option_vars.get(spec.key)
        if var is None:
            var = ctk.BooleanVar(value=option.default)
            self._option_vars[spec.key] = var

        checkbox: ctk.CTkCheckBox = ctk.CTkCheckBox(
            master=self.tab(tab_name),
            text=self._translator.get(option.label_key),
            variable=var,
            font=("Helvetica", 12),
            text_color="#FFA500",
        )
        if option.tooltip_key:
            tooltip.attach(checkbox, self._translator.get(option.tooltip_key))
        self._option_widgets[spec.key] = checkbox

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    @property
    def active_tool(self) -> str:
        """Clave de la herramienta seleccionada en la pestaña visible."""
        category: str | None = self._tab_to_category.get(self.get())
        if category is None:
            return ""
        return self._selection[category].get()

    @property
    def active_spec(self) -> ToolSpec | None:
        return self._registry.spec(self.active_tool)

    def refresh_options(self) -> None:
        """Muestra solo la casilla de la herramienta activa."""
        active: str = self.active_tool
        for key, checkbox in self._option_widgets.items():
            if key == active:
                checkbox.pack(side="left", padx=10)
            else:
                checkbox.pack_forget()

    def apply_options(self, module: Any) -> None:
        """Traslada al módulo el valor de su casilla antes de ejecutarlo."""
        spec: ToolSpec | None = self.active_spec
        if spec is None or spec.option is None:
            return

        var: ctk.BooleanVar | None = self._option_vars.get(spec.key)
        setter = getattr(module, spec.option.setter, None)
        if var is None or setter is None:
            logger.warning(
                "No se pudo aplicar la opción '%s' sobre %s.",
                spec.option.setter,
                spec.key,
            )
            return
        setter(var.get())

    def _handle_tab_change(self) -> None:
        self._on_change()
