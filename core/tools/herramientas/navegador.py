from __future__ import annotations

from typing import Any

from comandos.navegador import (
    buscar_en_web,
    es_comando_navegador,
    navegador_inteligente,
)
from core.tools.contratos import Parametro, Tool, ToolResult


def abrir_navegador(
    consulta: str | None = None,
    aplicacion: str | None = None,
    config: dict[str, Any] | None = None,
) -> ToolResult:
    """Abre el navegador con una busqueda web o con una aplicacion de navegacion.

    `consulta` viaja como dato estructurado: si es un comando de
    navegacion conocido ("busca X", "youtube", "chatgpt X") se resuelve
    como antes; si no, se trata como una busqueda web generica.
    """
    if aplicacion is not None:
        from core.tools.herramientas.aplicaciones import abrir_aplicacion

        return abrir_aplicacion(aplicacion=aplicacion, config=config)

    if consulta:
        consulta = consulta.strip()

        if es_comando_navegador(consulta):
            resultado = navegador_inteligente(consulta)
        else:
            resultado = buscar_en_web(consulta)

        if resultado:
            return ToolResult(
                exito=True,
                mensaje="Navegador abierto.",
                tool="abrir_navegador",
                datos={"consulta": consulta},
            )

    return ToolResult(
        exito=False,
        mensaje="No pude abrir el navegador.",
        tool="abrir_navegador",
        error="Fallo al abrir el navegador.",
        tipo_error="error_navegador",
    )


TOOL_ABRIR_NAVEGADOR = Tool(
    name="abrir_navegador",
    description="Abre el navegador para buscar informacion o para visitar una aplicacion de navegacion.",
    parametros=(
        Parametro("consulta", requerido=False, tipo=str, descripcion="Busqueda o url a abrir."),
        Parametro("aplicacion", requerido=False, tipo=str, descripcion="Navegador concreto a abrir."),
        Parametro("config", requerido=False, tipo=dict, descripcion="Configuracion de permisos del sistema."),
    ),
    ejecutor=abrir_navegador,
)

TOOLS = (TOOL_ABRIR_NAVEGADOR,)