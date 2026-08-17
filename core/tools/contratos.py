from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal


POLITICA_AUTO = "auto"
POLITICA_CONFIRMAR = "confirmar"
POLITICA_BLOQUEAR = "bloquear"


class ToolError(Exception):
    """Error de registro o de ejecucion de una Tool."""


class ToolNoEncontrada(ToolError):
    """Se pidio una Tool que no existe en el registro."""


@dataclass(frozen=True)
class Parametro:
    nombre: str
    requerido: bool = False
    tipo: type = str
    descripcion: str = ""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    ejecutor: Callable[..., "ToolResult"] = field(repr=False)
    parametros: tuple[Parametro, ...] = ()
    politica: str = POLITICA_AUTO


@dataclass(frozen=True)
class ToolResult:
    exito: bool
    mensaje: str
    tool: str
    datos: dict[str, Any] | None = None
    error: str | None = None
    tipo_error: str | None = None


TipoErrorValor = Literal[
    "parametros_invalidos",
    "aplicacion_no_registrada",
    "error_ejecucion",
    "permiso_denegado",
    "error_navegador",
]


def validar_parametros(
    parametros: tuple[Parametro, ...], valores: dict[str, Any]
) -> dict[str, Any]:
    """Valida y devuelve los parametros recibidos contra el esquema de la Tool."""
    validos: dict[str, Any] = {}

    for parametro in parametros:
        valor = valores.get(parametro.nombre)

        if valor is None:
            if parametro.requerido:
                raise ToolError(
                    f"El parametro requerido {parametro.nombre!r} es obligatorio."
                )
            continue

        if not isinstance(valor, parametro.tipo):
            raise ToolError(
                f"El parametro {parametro.nombre!r} debe ser de tipo "
                f"{parametro.tipo.__name__}, se recibio {type(valor).__name__}."
            )

        validos[parametro.nombre] = valor

    return validos