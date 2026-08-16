from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Skill:
    """Capacidad especializada que ORION puede describir y consultar.

    Una Skill describe qué hace ORION, cuándo debe usarse, qué herramientas
    relacionadas puede emplear y qué reglas aplican. No ejecuta acciones.
    """

    name: str
    description: str
    instructions: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


class SkillNoEncontrada(LookupError):
    """Se lanza cuando se pide una Skill que no existe en el registro."""

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        super().__init__(f"No existe una skill llamada {nombre!r}.")