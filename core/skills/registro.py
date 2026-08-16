from __future__ import annotations

from pathlib import Path

from core.skills.contratos import Skill, SkillNoEncontrada
from core.skills.lector import leer_skill


_DIRECTORIO_SKILLS = Path(__file__).resolve().parent


class SkillRegistry:
    """Registro que descubre y consulta las Skills disponibles."""

    def __init__(self, raiz: str | Path | None = None) -> None:
        self._raiz = Path(raiz) if raiz is not None else _DIRECTORIO_SKILLS
        self._skills: dict[str, Skill] = {}
        self._escaneado = False

    def descubrir(self) -> list[Skill]:
        """Escanea el directorio de Skills y devuelve las encontradas."""
        self._skills = {}
        self._escaneado = True

        if not self._raiz.is_dir():
            return []

        for entrada in sorted(self._raiz.iterdir()):
            if not entrada.is_dir():
                continue
            skill = leer_skill(entrada)
            if skill is not None:
                self._skills[skill.name] = skill

        return list(self._skills.values())

    def listar(self) -> list[Skill]:
        """Devuelve las Skills conocidas, escaneando solo si aun no se hizo."""
        if not self._escaneado:
            self.descubrir()
        return list(self._skills.values())

    def nombres(self) -> list[str]:
        return [skill.name for skill in self.listar()]

    def obtener(self, nombre: str) -> Skill:
        """Devuelve la Skill por nombre o lanza SkillNoEncontrada."""
        if not self._escaneado:
            self.descubrir()
        try:
            return self._skills[nombre]
        except KeyError:
            raise SkillNoEncontrada(nombre) from None


_REGISTRO = SkillRegistry()


def skills_disponibles() -> list[Skill]:
    return _REGISTRO.listar()


def obtener_skill(nombre: str) -> Skill:
    return _REGISTRO.obtener(nombre)