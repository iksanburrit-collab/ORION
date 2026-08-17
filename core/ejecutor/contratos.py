"""Contratos del ejecutor secuencial de planes (Fase 5).

El ejecutor recibe un Plan y ejecuta sus pasos EN ORDEN a traves del
ToolRegistry. No recibe texto del usuario: los parametros salen del Paso
planificado y de las Tools registradas. Es deterministico y no modifica
el Plan original.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.planificador.contratos import Paso, Plan


ESTADO_PENDIENTE = "pendiente"
ESTADO_EJECUTADO = "ejecutado"
ESTADO_EXITOSO = "exitoso"
ESTADO_FALLIDO = "fallido"
ESTADO_BLOQUEADO = "bloqueado"
ESTADO_OMITIDO = "omitido"
ESTADO_REQUIERE_CONFIRMACION = "requiere_confirmacion"


ESTADOS_EJECUCION = (
    ESTADO_PENDIENTE,
    ESTADO_EJECUTADO,
    ESTADO_EXITOSO,
    ESTADO_FALLIDO,
    ESTADO_BLOQUEADO,
    ESTADO_OMITIDO,
    ESTADO_REQUIERE_CONFIRMACION,
)


ESTADOS_EFECTIVOS = (ESTADO_PENDIENTE, ESTADO_EJECUTADO, ESTADO_EXITOSO, ESTADO_FALLIDO)


@dataclass(frozen=True)
class ResultadoPaso:
    """Resultado de un paso del Plan tras su ejecucion."""

    paso: Paso
    estado: str
    ejecutado: bool
    exito: bool
    respuesta: str = ""
    error: str | None = None
    datos: dict[str, Any] | None = None
    solicitud: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResultadoEjecucion:
    """Resultado acumulado de la ejecucion secuencial de un Plan."""

    plan: Plan
    resultados: tuple[ResultadoPaso, ...] = ()
    exito: bool = False
    respuesta_compuesta: str = ""
    metadatos: dict[str, Any] = field(default_factory=dict)
    requiere_confirmacion: bool = False
    paso_pendiente: ResultadoPaso | None = None
    solicitud: dict[str, Any] | None = None

    def pasos_ejecutados(self) -> list[ResultadoPaso]:
        return [resultado for resultado in self.resultados if resultado.ejecutado]

    def pasos_fallidos(self) -> list[ResultadoPaso]:
        return [resultado for resultado in self.resultados if resultado.estado == ESTADO_FALLIDO]

    def pasos_bloqueados(self) -> list[ResultadoPaso]:
        return [resultado for resultado in self.resultados if resultado.estado == ESTADO_BLOQUEADO]

    def pasos_omitidos(self) -> list[ResultadoPaso]:
        return [resultado for resultado in self.resultados if resultado.estado == ESTADO_OMITIDO]

    def pasos_con_confirmacion(self) -> list[ResultadoPaso]:
        return [
            resultado
            for resultado in self.resultados
            if resultado.estado == ESTADO_REQUIERE_CONFIRMACION
        ]

    def resultados_previos(self) -> list[ResultadoPaso]:
        """Resultados anteriores al paso pendiente (sin incluirlo)."""
        if self.paso_pendiente is None:
            return list(self.resultados)
        return [
            resultado
            for resultado in self.resultados
            if resultado is not self.paso_pendiente
        ]