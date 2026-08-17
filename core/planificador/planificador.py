"""Planificador determinista de ORION (Fase 2).

Transforma un Analisis (interprete) en un Plan de pasos resueltos
contra el registro de Tools. No ejecuta acciones ni modifica memoria:
solo alcanza el estado "planificable".
"""

from __future__ import annotations

from core.interprete.contratos import Analisis
from core.planificador.contratos import ESTADO_PLANIFICABLE, Plan
from core.planificador.resolucion import resolver_operacion
from core.tools.registro import ToolRegistry


_REGISTRO_DEFECTO = ToolRegistry()


def planificar(
    analisis: Analisis | None = None,
    registro: ToolRegistry | None = None,
) -> Plan:
    """Convierte un Analisis en un Plan determinista, sin ejecutar nada."""
    if analisis is None:
        return Plan(texto_original="", reconocido=False, resoluble=False)

    registro_activo = registro or _REGISTRO_DEFECTO

    pasos = tuple(
        resolver_operacion(operacion, registro_activo)
        for operacion in analisis.operaciones
    )

    errores = tuple(
        paso.motivo for paso in pasos if paso.estado != ESTADO_PLANIFICABLE
    )

    return Plan(
        texto_original=analisis.texto_original,
        pasos=pasos,
        reconocido=bool(analisis),
        resoluble=any(paso.estado == ESTADO_PLANIFICABLE for paso in pasos),
        errores=errores,
        advertencias=analisis.fragmentos_no_reconocidos,
        metadatos={"cantidad_pasos": len(pasos)},
    )