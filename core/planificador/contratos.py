"""Contratos del planificador de ORION.

El planificador convierte el Analisis (interprete) en un Plan
determinista de pasos. Esta fase solo planifica: decide si cada
operacion puede resolverse con una Tool conocida, sin ejecutarla y
sin tocar el cerebro ni la memoria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.interprete.contratos import Entidad


ESTADO_PLANIFICABLE = "planificable"
ESTADO_SIN_TOOL = "sin_tool"
ESTADO_ENTIDAD_INSUFICIENTE = "entidad_insuficiente"
ESTADO_ENTIDAD_INCOMPATIBLE = "entidad_incompatible"
ESTADO_NO_PLANIFICABLE = "no_planificable"


ESTADOS = (
    ESTADO_PLANIFICABLE,
    ESTADO_SIN_TOOL,
    ESTADO_ENTIDAD_INSUFICIENTE,
    ESTADO_ENTIDAD_INCOMPATIBLE,
    ESTADO_NO_PLANIFICABLE,
)


@dataclass(frozen=True)
class Paso:
    """Paso concreto del plan: operacion resuelta contra una Tool o no."""

    orden: int
    verbo: str
    entidad: Entidad | None
    tool: str | None
    parametros: dict[str, Any]
    estado: str
    motivo: str
    texto: str


@dataclass(frozen=True)
class Plan:
    """Plan determinista derivado de un Analisis, sin ejecutar acciones."""

    texto_original: str
    pasos: tuple[Paso, ...] = ()
    reconocido: bool = False
    resoluble: bool = False
    errores: tuple[str, ...] = ()
    advertencias: tuple[str, ...] = ()
    metadatos: dict[str, Any] = field(default_factory=dict)

    def pasos_planificables(self) -> list[Paso]:
        """Pasos que pueden resolverse con una Tool registrada."""
        return [paso for paso in self.pasos if paso.estado == ESTADO_PLANIFICABLE]

    def pasos_no_planificables(self) -> list[Paso]:
        """Pasos que no pueden resolverse (sin Tool o entidad invalida)."""
        return [paso for paso in self.pasos if paso.estado != ESTADO_PLANIFICABLE]