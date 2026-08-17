"""Contratos del interprete de comandos de ORION.

El interprete convierte lenguaje natural en una estructura tipada
(Analisis -> Operacion -> Entidad) que el planificador podra consumir
en una fase posterior. Esta fase solo analiza: no resuelve entidades
ni ejecuta acciones.
"""

from __future__ import annotations

from dataclasses import dataclass


TIPO_APLICACION = "aplicacion"
TIPO_CONSULTA = "consulta"
TIPO_PROYECTO = "proyecto"
TIPO_TAREA = "tarea"
TIPO_COLECCION = "coleccion"
TIPO_OBJETO = "objeto"


TIPOS_ENTIDAD = (
    TIPO_APLICACION,
    TIPO_CONSULTA,
    TIPO_PROYECTO,
    TIPO_TAREA,
    TIPO_COLECCION,
    TIPO_OBJETO,
)


@dataclass(frozen=True)
class Entidad:
    """Objeto sobre el que actua una operacion.

    `valor` conserva el texto original (mayusculas y acentos); `normalizado`
    es la forma canonica para busquedas posteriores del planificador.
    """

    tipo: str
    valor: str
    normalizado: str = ""


@dataclass(frozen=True)
class Operacion:
    """Accion unica extraida del texto del usuario.

    `verbo` es el nombre canonico de la capacidad (p. ej. "abrir"); `orden`
    es la posicion de la operacion dentro de la secuencia analizada.
    """

    verbo: str
    entidad: Entidad | None = None
    orden: int = 0
    texto: str = ""


@dataclass(frozen=True)
class Analisis:
    """Resultado del analisis de un comando en lenguaje natural."""

    texto_original: str
    operaciones: tuple[Operacion, ...] = ()
    reconocido: bool = False
    fragmentos_no_reconocidos: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.reconocido