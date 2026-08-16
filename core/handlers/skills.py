from __future__ import annotations

from typing import Any

from core.skills import skills_disponibles


_CONSULTAS_SKILLS = frozenset({
    "que skills tienes",
    "cuales skills tienes",
    "cuáles skills tienes",
    "lista skills",
    "lista tus skills",
    "muestra tus skills",
    "cuales son tus skills",
    "cuáles son tus skills",
    "que capacidades tienes",
    "lista capacidades",
})


def puede_manejar_skills(texto: str) -> bool:
    return texto in _CONSULTAS_SKILLS


def procesar_skills(texto: str) -> tuple[bool, str, str, dict[str, Any] | None]:
    if not puede_manejar_skills(texto):
        return False, "", "", None

    skills = skills_disponibles()
    if not skills:
        return True, "listar_skills", "No hay skills disponibles.", None

    lineas = [f"Skills disponibles: {len(skills)}"]
    lineas.extend(f"- {skill.name}: {skill.description}" for skill in skills)
    return True, "listar_skills", "\n".join(lineas), None