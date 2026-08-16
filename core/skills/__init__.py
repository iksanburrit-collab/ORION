"""Sistema de Skills de ORION (Fase 1).

Una Skill describe una capacidad especializada de ORION: qué hace, cuándo
usarla, qué herramientas relacionadas puede emplear y qué reglas aplican.
El registro permite descubrir y consultar las Skills sin cambiar el flujo
normal de procesamiento de ORION.
"""

from core.skills.contratos import Skill, SkillNoEncontrada
from core.skills.registro import (
    SkillRegistry,
    obtener_skill,
    skills_disponibles,
)

__all__ = [
    "Skill",
    "SkillNoEncontrada",
    "SkillRegistry",
    "obtener_skill",
    "skills_disponibles",
]