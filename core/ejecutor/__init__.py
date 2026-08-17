"""Ejecutor secuencial de planes (Fase 5).

Ejecuta los pasos de un Plan en orden, de forma determinista, usando el
ToolRegistry y la puerta de permisos ya integrada en las Tools.
"""

from core.ejecutor.contratos import (
    ESTADO_BLOQUEADO,
    ESTADO_EJECUTADO,
    ESTADO_EXITOSO,
    ESTADO_FALLIDO,
    ESTADO_OMITIDO,
    ESTADO_PENDIENTE,
    ESTADOS_EJECUCION,
    ResultadoEjecucion,
    ResultadoPaso,
)
from core.ejecutor.ejecutor import EjecutorPlan

__all__ = [
    "ESTADO_BLOQUEADO",
    "ESTADO_EJECUTADO",
    "ESTADO_EXITOSO",
    "ESTADO_FALLIDO",
    "ESTADO_OMITIDO",
    "ESTADO_PENDIENTE",
    "ESTADOS_EJECUCION",
    "ResultadoEjecucion",
    "ResultadoPaso",
    "EjecutorPlan",
]