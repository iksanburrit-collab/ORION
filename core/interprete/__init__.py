"""Interprete de comandos de ORION (Fase 1).

Convierte lenguaje natural en una estructura tipada (Analisis ->
Operacion -> Entidad) que el planificador consumira en la siguiente
fase. Esta fase no resuelve entidades ni ejecuta acciones.
"""

from core.interprete.contratos import (
    TIPO_APLICACION,
    TIPO_COLECCION,
    TIPO_CONSULTA,
    TIPO_OBJETO,
    TIPO_PROYECTO,
    TIPO_TAREA,
    Analisis,
    Entidad,
    Operacion,
)
from core.interprete.verbos import (
    REGISTRO_VERBOS_BASE,
    RegistroVerbos,
    Verbo,
    verbos_disponibles,
)
from core.interprete.analizador import analizar

__all__ = [
    "TIPO_APLICACION",
    "TIPO_COLECCION",
    "TIPO_CONSULTA",
    "TIPO_OBJETO",
    "TIPO_PROYECTO",
    "TIPO_TAREA",
    "Analisis",
    "Entidad",
    "Operacion",
    "REGISTRO_VERBOS_BASE",
    "RegistroVerbos",
    "Verbo",
    "analizar",
    "verbos_disponibles",
]