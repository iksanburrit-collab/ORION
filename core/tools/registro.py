from __future__ import annotations

from typing import Any

from core.tools.contratos import Tool, ToolError, ToolNoEncontrada, ToolResult, validar_parametros
from core.tools.herramientas import aplicaciones, navegador


class ToolRegistry:
    """Registro de Tools ejecutables, similar al registro de Skills."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._base_registrada = False

    def registrar(self, tool: Tool) -> None:
        self._asegurar_base()
        if tool.name in self._tools:
            raise ToolError(f"Ya existe una Tool registrada como {tool.name!r}.")
        self._tools[tool.name] = tool

    def descubrir(self) -> list[Tool]:
        """Registra las Tools base y devuelve todas las disponibles."""
        if not self._base_registrada:
            for herramienta in (aplicaciones.TOOLS, navegador.TOOLS):
                for tool in herramienta:
                    if tool.name not in self._tools:
                        self._tools[tool.name] = tool
            self._base_registrada = True
        return self.listar()

    def listar(self) -> list[Tool]:
        self._asegurar_base()
        return list(self._tools.values())

    def nombres(self) -> list[str]:
        self._asegurar_base()
        return sorted(self._tools.keys())

    def existe(self, nombre: str) -> bool:
        self._asegurar_base()
        return nombre in self._tools

    def obtener(self, nombre: str) -> Tool:
        self._asegurar_base()
        try:
            return self._tools[nombre]
        except KeyError as exc:
            raise ToolNoEncontrada(f"No existe la Tool {nombre!r}.") from exc

    def ejecutar(self, nombre: str, parametros: dict[str, Any] | None = None) -> ToolResult:
        parametros = parametros or {}
        tool = self.obtener(nombre)
        try:
            validos = validar_parametros(tool.parametros, parametros)
        except ToolError as exc:
            return ToolResult(
                exito=False,
                mensaje=str(exc),
                tool=nombre,
                error=str(exc),
                tipo_error="parametros_invalidos",
            )

        try:
            return tool.ejecutor(**validos)
        except ToolError as exc:
            return ToolResult(
                exito=False,
                mensaje=str(exc),
                tool=nombre,
                error=str(exc),
                tipo_error="error_ejecucion",
            )

    def _asegurar_base(self) -> None:
        if not self._base_registrada:
            self.descubrir()


_REGISTRO = ToolRegistry()


def herramientas_disponibles() -> list[str]:
    return _REGISTRO.nombres()


def obtener_herramienta(nombre: str) -> Tool:
    return _REGISTRO.obtener(nombre)


def existe_herramienta(nombre: str) -> bool:
    return _REGISTRO.existe(nombre)


def ejecutar_herramienta(nombre: str, parametros: dict[str, Any] | None = None) -> ToolResult:
    return _REGISTRO.ejecutar(nombre, parametros)