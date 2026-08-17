"""Ejecutor secuencial de planes (Fase 5).

Recibe un Plan y ejecuta sus pasos EN ORDEN a traves del ToolRegistry.
La puerta de permisos (EjecutorAccionesPC) ya vive dentro de las Tools
de acciones de PC; el ejecutor no crea una segunda puerta y no conoce el
texto del usuario.
"""

from __future__ import annotations

from core.ejecutor.contratos import (
    ESTADO_BLOQUEADO,
    ESTADO_EXITOSO,
    ESTADO_FALLIDO,
    ESTADO_OMITIDO,
    ResultadoEjecucion,
    ResultadoPaso,
)
from core.planificador.contratos import ESTADO_PLANIFICABLE, Paso, Plan
from core.tools.contratos import ToolResult
from core.tools.registro import ToolRegistry


_REGISTRO_DEFECTO = ToolRegistry()


class EjecutorPlan:
    """Ejecuta un Plan paso a paso, de forma determinista y secuencial."""

    def __init__(self, registro: ToolRegistry | None = None) -> None:
        self._registro = registro or _REGISTRO_DEFECTO

    def ejecutar(self, plan: Plan) -> ResultadoEjecucion:
        resultados = []
        detenido = False

        for paso in plan.pasos:
            if detenido:
                resultados.append(_resultado_bloqueado(paso))
                continue

            if not _es_ejecutable(paso):
                resultados.append(_resultado_omitido(paso))
                continue

            if not self._registro.existe(paso.tool):
                resultados.append(
                    _resultado_fallido(
                        paso,
                        f"La Tool {paso.tool!r} no esta registrada.",
                        ejecutado=False,
                    )
                )
                detenido = True
                continue

            try:
                resultado_tool = self._registro.ejecutar(paso.tool, paso.parametros)
            except Exception as exc:
                resultados.append(
                    _resultado_fallido(
                        paso,
                        f"Error al ejecutar la Tool {paso.tool!r}: {exc}",
                        ejecutado=True,
                    )
                )
                detenido = True
                continue

            if resultado_tool.exito:
                resultados.append(_resultado_exitoso(paso, resultado_tool))
            else:
                resultados.append(
                    _resultado_fallido(
                        paso,
                        _mensaje_fallo(resultado_tool),
                        tool_result=resultado_tool,
                    )
                )
                detenido = True

        return ResultadoEjecucion(
            plan=plan,
            resultados=tuple(resultados),
            exito=not any(resultado.estado == ESTADO_FALLIDO for resultado in resultados),
            respuesta_compuesta=_respuesta_compuesta(resultados),
        )


def _es_ejecutable(paso: Paso) -> bool:
    return paso.estado == ESTADO_PLANIFICABLE and paso.tool is not None


def _resultado_exitoso(paso: Paso, tool_result: ToolResult) -> ResultadoPaso:
    return ResultadoPaso(
        paso=paso,
        estado=ESTADO_EXITOSO,
        ejecutado=True,
        exito=True,
        respuesta=tool_result.mensaje,
        datos=tool_result.datos,
    )


def _resultado_fallido(
    paso: Paso,
    motivo: str,
    tool_result: ToolResult | None = None,
    ejecutado: bool | None = None,
) -> ResultadoPaso:
    return ResultadoPaso(
        paso=paso,
        estado=ESTADO_FALLIDO,
        ejecutado=(
            ejecutado if ejecutado is not None else tool_result is not None
        ),
        exito=False,
        respuesta=motivo,
        error=motivo,
        datos=tool_result.datos if tool_result is not None else None,
    )


def _resultado_bloqueado(paso: Paso) -> ResultadoPaso:
    return ResultadoPaso(
        paso=paso,
        estado=ESTADO_BLOQUEADO,
        ejecutado=False,
        exito=False,
        error="Paso no ejecutado: un paso anterior fallo.",
    )


def _resultado_omitido(paso: Paso) -> ResultadoPaso:
    return ResultadoPaso(
        paso=paso,
        estado=ESTADO_OMITIDO,
        ejecutado=False,
        exito=False,
        error=paso.motivo or "Paso omitido: no es ejecutable.",
    )


def _mensaje_fallo(tool_result: ToolResult) -> str:
    return tool_result.error or tool_result.mensaje or "Fallo al ejecutar la Tool."


def _respuesta_compuesta(resultados: list[ResultadoPaso]) -> str:
    return "\n".join(
        resultado.respuesta or resultado.error
        for resultado in resultados
        if (resultado.respuesta or resultado.error)
    )