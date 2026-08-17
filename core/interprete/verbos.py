"""Vocabulario de verbos del interprete.

Los verbos definen que acciones reconoce ORION y con que sinonimos.
El RegistroVerbos es la abstraccion sobre la que, en el futuro, se
pueden registrar verbos provenientes de Skills o Tools sin modificar
el analizador.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.interprete.contratos import (
    TIPO_APLICACION,
    TIPO_COLECCION,
    TIPO_CONSULTA,
    TIPO_OBJETO,
    TIPO_TAREA,
)


@dataclass(frozen=True)
class Verbo:
    """Capacidad accionable que ORION puede reconocer."""

    nombre: str
    sinonimos: tuple[str, ...]
    tipo_entidad: str = TIPO_APLICACION


VERBOS_BASE = (
    Verbo("abrir", ("abre", "abrir", "abreme", "lanza", "lanzar"), TIPO_APLICACION),
    Verbo("cerrar", ("cierra", "cerrar", "termina", "terminar"), TIPO_APLICACION),
    Verbo("iniciar", ("inicia", "iniciar"), TIPO_APLICACION),
    Verbo("buscar", ("busca", "buscar", "buscame"), TIPO_CONSULTA),
    Verbo("ejecutar", ("ejecuta", "ejecutar", "corre", "correr"), TIPO_TAREA),
    Verbo("listar", ("lista", "listar", "muestrame", "muestra"), TIPO_COLECCION),
    Verbo("crear", ("crea", "crear", "agrega", "agregar", "nueva"), TIPO_OBJETO),
    Verbo("consultar", ("consulta", "consultar", "dime", "cuentame"), TIPO_CONSULTA),
)


class RegistroVerbos:
    """Catalogo de verbos consultables por sinonimo.

    Permite inyectar un catalogo propio (por ejemplo, construido desde
    las Skills o Tools) sin cambiar el analizador.
    """

    def __init__(self, verbos: Iterable[Verbo] | None = None) -> None:
        self._verbos = tuple(verbos) if verbos is not None else VERBOS_BASE
        self._por_sinonimo: dict[str, Verbo] = {}

        for verbo in self._verbos:
            for sinonimo in (verbo.nombre,) + verbo.sinonimos:
                self._por_sinonimo.setdefault(sinonimo, verbo)

    def todos(self) -> tuple[Verbo, ...]:
        return self._verbos

    def nombres(self) -> list[str]:
        return [verbo.nombre for verbo in self._verbos]

    def buscar_por_sinonimo(self, palabra: str) -> Verbo | None:
        return self._por_sinonimo.get(palabra)


REGISTRO_VERBOS_BASE = RegistroVerbos()


def verbos_disponibles() -> list[str]:
    """Nombres de los verbos base reconocidos por ORION."""
    return REGISTRO_VERBOS_BASE.nombres()