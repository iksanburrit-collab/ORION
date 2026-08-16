from __future__ import annotations

from typing import Any

from core.conocimiento.normalizacion import normalizar_para_busqueda
from core.tools.contratos import Parametro, Tool, ToolResult
from servicios.sistema.aplicaciones import CatalogoAplicaciones
from servicios.sistema.ejecutor import EjecutorAccionesPC


def _catalogo_por_defecto() -> CatalogoAplicaciones:
    return CatalogoAplicaciones()


def _desde_resultado_accion(resultado) -> ToolResult:
    return ToolResult(
        exito=resultado.exito,
        mensaje=resultado.mensaje,
        tool="abrir_aplicacion",
        datos={"resultado": resultado.mensaje},
        error=resultado.error,
        tipo_error=resultado.tipo_error,
    )


def abrir_aplicacion(
    aplicacion: str,
    config: dict[str, Any] | None = None,
) -> ToolResult:
    """Abre una aplicacion registrada. La ejecucion pasa por la puerta de permisos."""
    ej = EjecutorAccionesPC(config or {})
    resultado, _solicitud = ej.preparar("abrir_aplicacion", {"aplicacion": aplicacion})
    return _desde_resultado_accion(resultado)


def listar_aplicaciones(
    catalogo: CatalogoAplicaciones | None = None,
) -> ToolResult:
    """Devuelve las aplicaciones disponibles con identificadores y alias."""
    catalogo = catalogo or _catalogo_por_defecto()
    registradas = catalogo.listar()

    aplicaciones = [
        {
            "nombre": app.nombre,
            "identificador": normalizar_para_busqueda(app.nombre),
            "origen": getattr(app, "origen", "manual"),
            "comando": app.ruta,
            "alias": list(app.aliases),
        }
        for app in registradas
    ]

    return ToolResult(
        exito=True,
        mensaje=f"Aplicaciones registradas: {len(aplicaciones)}",
        tool="listar_aplicaciones",
        datos={"aplicaciones": aplicaciones},
    )


TOOL_ABRIR_APLICACION = Tool(
    name="abrir_aplicacion",
    description=(
        "Abre una aplicacion ya registrada en el sistema. El nombre se "
        "resuelve contra el catalogo y solo se ejecutan programas conocidos."
    ),
    parametros=(
        Parametro("aplicacion", requerido=True, tipo=str, descripcion="Nombre o alias de la aplicacion."),
        Parametro("config", requerido=False, tipo=dict, descripcion="Configuracion de permisos del sistema."),
    ),
    ejecutor=abrir_aplicacion,
)

TOOL_LISTAR_APLICACIONES = Tool(
    name="listar_aplicaciones",
    description="Devuelve las aplicaciones disponibles en el sistema con sus identificadores y alias.",
    parametros=(
        Parametro("catalogo", requerido=False, tipo=CatalogoAplicaciones, descripcion="Catalogo opcional para pruebas."),
    ),
    ejecutor=listar_aplicaciones,
)

TOOLS = (TOOL_ABRIR_APLICACION, TOOL_LISTAR_APLICACIONES)