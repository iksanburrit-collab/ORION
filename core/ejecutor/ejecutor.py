"""Ejecutor secuencial de planes (Fase 5).

Recibe un Plan y ejecuta sus pasos EN ORDEN a traves del ToolRegistry.
La puerta de permisos (EjecutorAccionesPC) ya vive dentro de las Tools
de acciones de PC; el ejecutor no crea una segunda puerta y no conoce el
texto del usuario.
"""

from __future__ import annotations

from typing import Any

from core.ejecutor.contratos import (
    ESTADO_BLOQUEADO,
    ESTADO_EXITOSO,
    ESTADO_FALLIDO,
    ESTADO_OMITIDO,
    ESTADO_REQUIERE_CONFIRMACION,
    ResultadoEjecucion,
    ResultadoPaso,
)
from core.planificador.contratos import ESTADO_PLANIFICABLE, Paso, Plan
from core.tools.contratos import (
    POLITICA_BLOQUEAR,
    POLITICA_CONFIRMAR,
    ToolResult,
)
from core.tools.registro import ToolRegistry


_REGISTRO_DEFECTO = ToolRegistry()


class EjecutorPlan:
    """Ejecuta un Plan paso a paso, de forma determinista y secuencial."""

    def __init__(self, registro: ToolRegistry | None = None) -> None:
        self._registro = registro or _REGISTRO_DEFECTO

    def ejecutar(
        self,
        plan: Plan,
        config: dict[str, Any] | None = None,
        autorizado: set[int] | frozenset[int] | None = None,
    ) -> ResultadoEjecucion:
        """Ejecuta un Plan paso a paso, de forma determinista y secuencial.

        `autorizado` contiene los `orden` de pasos CONFIRMAR que el usuario
        ya autorizo de forma explicita: se ejecutan como AUTO en esta
        ejecucion (una sola vez), sin convertir la politica de la Tool en
        AUTO de forma permanente. El resto de pasos se vuelven a evaluar.
        """
        autorizado = autorizado if autorizado is not None else set()
        resultados = []
        detenido = False
        esperando_confirmacion = False
        paso_pendiente: ResultadoPaso | None = None

        for paso in plan.pasos:
            if esperando_confirmacion:
                break

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

            politica = self._registro.obtener(paso.tool).politica

            if politica == POLITICA_BLOQUEAR:
                resultados.append(_resultado_bloqueado_por_politica(paso))
                detenido = True
                continue

            if politica == POLITICA_CONFIRMAR and paso.orden not in autorizado:
                solicitud = _solicitud_confirmacion(paso)
                resultado_paso = _resultado_requiere_confirmacion(paso, solicitud)
                resultados.append(resultado_paso)
                paso_pendiente = resultado_paso
                esperando_confirmacion = True
                continue

            parametros = paso.parametros
            if config is not None:
                parametros = {**parametros, "config": config}

            try:
                resultado_tool = self._registro.ejecutar(paso.tool, parametros)
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

        requiere_confirmacion = esperando_confirmacion

        return ResultadoEjecucion(
            plan=plan,
            resultados=tuple(resultados),
            exito=not any(
                resultado.estado == ESTADO_FALLIDO for resultado in resultados
            ),
            respuesta_compuesta=_respuesta_compuesta(resultados),
            requiere_confirmacion=requiere_confirmacion,
            paso_pendiente=paso_pendiente,
            solicitud=(
                paso_pendiente.solicitud
                if paso_pendiente is not None and paso_pendiente.solicitud is not None
                else None
            ),
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


def _resultado_bloqueado_por_politica(paso: Paso) -> ResultadoPaso:
    return ResultadoPaso(
        paso=paso,
        estado=ESTADO_BLOQUEADO,
        ejecutado=False,
        exito=False,
        error=(
            f"La Tool {paso.tool!r} esta bloqueada por politica "
            "y no puede ejecutarse automaticamente."
        ),
    )


def _resultado_requiere_confirmacion(
    paso: Paso,
    solicitud: dict[str, Any],
) -> ResultadoPaso:
    return ResultadoPaso(
        paso=paso,
        estado=ESTADO_REQUIERE_CONFIRMACION,
        ejecutado=False,
        exito=False,
        respuesta=solicitud["texto_confirmacion"],
        solicitud=solicitud,
    )


def _solicitud_confirmacion(paso: Paso) -> dict[str, Any]:
    return {
        "tipo": "confirmar_politica",
        "identificador": paso.tool or paso.verbo,
        "accion": paso.tool or paso.verbo,
        "tool": paso.tool,
        "paso": paso.orden,
        "motivo": "La Tool requiere autorizacion explicita del usuario.",
        "parametros": paso.parametros,
        "texto_confirmacion": (
            f"La accion del paso {paso.orden} "
            f"({paso.tool or paso.verbo}) requiere tu autorizacion. "
            "Quieres ejecutarla?"
        ),
    }


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