"""Resolucion determinista de operaciones contra el registro de Tools.

El planificador solo declara que Tool (si existe) resolveria cada
operacion y con que parametros. No ejecuta nada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.interprete.contratos import (
    TIPO_APLICACION,
    TIPO_COLECCION,
    TIPO_CONSULTA,
    Entidad,
    Operacion,
)
from core.planificador.contratos import (
    ESTADO_ENTIDAD_INCOMPATIBLE,
    ESTADO_ENTIDAD_INSUFICIENTE,
    ESTADO_NO_PLANIFICABLE,
    ESTADO_PLANIFICABLE,
    ESTADO_SIN_TOOL,
    Paso,
)
from core.tools.contratos import ToolError, validar_parametros
from core.tools.registro import ToolRegistry


@dataclass(frozen=True)
class PlanificacionVerbo:
    """Mapeo declarativo entre un verbo y la Tool que lo resolveria."""

    tool: str | None = None
    parametro: str | None = None
    tipos_entidad: tuple[str, ...] = ()
    normalizados_entidad: tuple[str, ...] = ()


MAPA_VERBOS: dict[str, PlanificacionVerbo] = {
    "abrir": PlanificacionVerbo(
        tool="abrir_aplicacion",
        parametro="aplicacion",
        tipos_entidad=(TIPO_APLICACION,),
    ),
    "iniciar": PlanificacionVerbo(
        tool="abrir_aplicacion",
        parametro="aplicacion",
        tipos_entidad=(TIPO_APLICACION,),
    ),
    "buscar": PlanificacionVerbo(
        tool="abrir_navegador",
        parametro="consulta",
        tipos_entidad=(TIPO_CONSULTA,),
    ),
    "listar": PlanificacionVerbo(
        tool="listar_aplicaciones",
        tipos_entidad=(TIPO_COLECCION,),
        normalizados_entidad=("aplicaciones",),
    ),
    "cerrar": PlanificacionVerbo(),
    "ejecutar": PlanificacionVerbo(),
    "crear": PlanificacionVerbo(),
    "consultar": PlanificacionVerbo(),
}


def resolver_operacion(operacion: Operacion, registro: ToolRegistry) -> Paso:
    """Resuelve una operacion a un Paso, sin ejecutar la Tool."""
    planificacion = MAPA_VERBOS.get(operacion.verbo)

    if planificacion is None:
        return _paso_simple(
            operacion,
            estado=ESTADO_NO_PLANIFICABLE,
            motivo=f"El verbo {operacion.verbo!r} no tiene planificacion definida.",
        )

    if planificacion.tool is None:
        return _paso_simple(
            operacion,
            estado=ESTADO_SIN_TOOL,
            motivo=f"No existe ninguna Tool para el verbo {operacion.verbo!r}.",
        )

    if not registro.existe(planificacion.tool):
        return _paso_simple(
            operacion,
            estado=ESTADO_SIN_TOOL,
            motivo=f"La Tool {planificacion.tool!r} no esta registrada.",
        )

    entidad = operacion.entidad

    if planificacion.parametro is not None and entidad is None:
        return _paso_simple(
            operacion,
            estado=ESTADO_ENTIDAD_INSUFICIENTE,
            tool=planificacion.tool,
            motivo=f"Falta la entidad para planificar el verbo {operacion.verbo!r}.",
        )

    if entidad is not None and not _entidad_compatible(entidad, planificacion):
        return _paso_simple(
            operacion,
            estado=ESTADO_ENTIDAD_INCOMPATIBLE,
            tool=planificacion.tool,
            motivo=(
                f"La entidad {entidad.valor!r} no es compatible con "
                f"la Tool {planificacion.tool!r}."
            ),
        )

    candidatos: dict[str, Any] = {}
    if planificacion.parametro is not None and entidad is not None:
        candidatos[planificacion.parametro] = entidad.valor

    try:
        parametros = validar_parametros(
            registro.obtener(planificacion.tool).parametros,
            candidatos,
        )
    except ToolError as exc:
        return _paso_simple(
            operacion,
            estado=ESTADO_ENTIDAD_INCOMPATIBLE,
            tool=planificacion.tool,
            motivo=str(exc),
        )

    return _paso_simple(
        operacion,
        estado=ESTADO_PLANIFICABLE,
        tool=planificacion.tool,
        parametros=parametros,
        motivo="Operacion planificada.",
    )


def _entidad_compatible(
    entidad: Entidad,
    planificacion: PlanificacionVerbo,
) -> bool:
    if planificacion.tipos_entidad and entidad.tipo not in planificacion.tipos_entidad:
        return False

    if (
        planificacion.normalizados_entidad
        and entidad.normalizado not in planificacion.normalizados_entidad
    ):
        return False

    return True


def _paso_simple(
    operacion: Operacion,
    estado: str,
    motivo: str,
    tool: str | None = None,
    parametros: dict[str, Any] | None = None,
) -> Paso:
    return Paso(
        orden=operacion.orden,
        verbo=operacion.verbo,
        entidad=operacion.entidad,
        tool=tool,
        parametros=parametros or {},
        estado=estado,
        motivo=motivo,
        texto=operacion.texto,
    )