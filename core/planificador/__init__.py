"""Planificador de ORION (Fase 2).

Convierte un Analisis (interprete) en un Plan determinista de pasos
resueltos contra el registro de Tools, sin ejecutar ninguna accion.
"""

from core.planificador.contratos import (
    ESTADO_ENTIDAD_INCOMPATIBLE,
    ESTADO_ENTIDAD_INSUFICIENTE,
    ESTADO_NO_PLANIFICABLE,
    ESTADO_PLANIFICABLE,
    ESTADO_SIN_TOOL,
    ESTADOS,
    Paso,
    Plan,
)
from core.planificador.planificador import planificar
from core.planificador.resolucion import MAPA_VERBOS, PlanificacionVerbo

__all__ = [
    "ESTADO_ENTIDAD_INCOMPATIBLE",
    "ESTADO_ENTIDAD_INSUFICIENTE",
    "ESTADO_NO_PLANIFICABLE",
    "ESTADO_PLANIFICABLE",
    "ESTADO_SIN_TOOL",
    "ESTADOS",
    "Paso",
    "Plan",
    "planificar",
    "MAPA_VERBOS",
    "PlanificacionVerbo",
]