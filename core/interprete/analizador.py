"""Analizador determinista de comandos en lenguaje natural.

Convierte el texto del usuario en un Analisis con una o varias
Operaciones. No resuelve entidades (eso corresponde al planificador)
ni ejecuta acciones.

Reglas de analisis:

- La primera palabra de cada clausula debe ser un verbo conocido.
- Los conectores dividen el texto en clausulas:
  * "y luego", "y despues", "y posteriormente", "luego", "despues" y
    "posteriormente" dividen si hay una accion despues del conector.
  * "y", "," y ";" dividen solo si la accion empieza justo despues.
- El conector "y" no divide cuando no va seguido de un verbo, para no
  partir nombres como "Visual Studio Code" o "rock y roll".
"""

from __future__ import annotations

import re

from core.conocimiento import normalizar_para_busqueda
from core.interprete.contratos import (
    Analisis,
    Entidad,
    Operacion,
    TIPO_PROYECTO,
    TIPO_TAREA,
)
from core.interprete.verbos import (
    REGISTRO_VERBOS_BASE,
    RegistroVerbos,
    Verbo,
)


_CONECTORES_MULTIPALABRA = frozenset({
    "y luego",
    "y despues",
    "y posteriormente",
})

_CONECTORES_SIMPLES = frozenset({
    "luego",
    "despues",
    "posteriormente",
})

_CONECTOR_SIMPLE_Y = "y"

_PUNTUACION_FINAL = re.compile(r"[,;:.!?¡¿]+$")

_PUNTUACION_SEPARADORA = re.compile(r"[,;]$")


def analizar(
    texto: str,
    registro_verbos: RegistroVerbos | None = None,
) -> Analisis:
    """Analiza un comando y devuelve las operaciones reconocidas."""
    if not texto or not texto.strip():
        return Analisis(texto_original=texto or "", reconocido=False)

    registro = registro_verbos or REGISTRO_VERBOS_BASE

    original = " ".join(texto.split())
    normalizado = normalizar_para_busqueda(original)

    tokens_norm = normalizado.split()
    tokens_orig = original.split()

    posiciones_verbo = _verbos_en(tokens_norm, registro)
    conectores = _conectores_en(tokens_norm)
    conectores_validos = _conectores_validos(
        tokens_norm,
        conectores,
        posiciones_verbo,
    )
    clausulas = _dividir_en_clausulas(conectores_validos, len(tokens_norm))

    operaciones = []
    no_reconocidos = []

    for orden, (inicio, fin) in enumerate(clausulas):
        operacion = _operacion_desde_clausula(
            tokens_norm,
            tokens_orig,
            inicio,
            fin,
            orden,
            registro,
        )

        if operacion is None:
            fragmento = " ".join(tokens_orig[inicio:fin])

            if fragmento:
                no_reconocidos.append(fragmento)
            continue

        operaciones.append(operacion)

    return Analisis(
        texto_original=original,
        operaciones=tuple(operaciones),
        reconocido=bool(operaciones),
        fragmentos_no_reconocidos=tuple(no_reconocidos),
    )


def _verbos_en(
    tokens: list[str],
    registro: RegistroVerbos,
) -> set[int]:
    """Devuelve las posiciones de los verbos reconocidos en los tokens."""
    posiciones: set[int] = set()

    for posicion, token in enumerate(tokens):
        if registro.buscar_por_sinonimo(token) is not None:
            posiciones.add(posicion)

    return posiciones


def _conectores_en(tokens: list[str]) -> list[tuple[int, int]]:
    """Devuelve los conectores candidatos como intervalos (inicio, fin).

    Los tokens en [inicio, fin) se descartan al dividir clausulas. Una
    coma o punto y coma pegados a un token ("Chrome,") produce un corte
    de ancho cero entre el token y el siguiente.
    """
    conectores = []
    cantidad = len(tokens)
    indice = 0

    while indice < cantidad:
        token = tokens[indice]

        if indice + 2 <= cantidad:
            combinacion = " ".join(tokens[indice:indice + 2])

            if combinacion in _CONECTORES_MULTIPALABRA:
                conectores.append((indice, indice + 2))
                indice += 2
                continue

        if token in _CONECTORES_SIMPLES:
            conectores.append((indice, indice + 1))
            indice += 1
            continue

        if token in (_CONECTOR_SIMPLE_Y, ",", ";"):
            conectores.append((indice, indice + 1))
            indice += 1
            continue

        if _PUNTUACION_SEPARADORA.search(token):
            conectores.append((indice + 1, indice + 1))

        indice += 1

    return conectores


def _conectores_validos(
    tokens: list[str],
    conectores: list[tuple[int, int]],
    posiciones_verbo: set[int],
) -> list[tuple[int, int]]:
    """Filtra los conectores que realmente separan dos acciones."""
    validos = []

    for inicio, fin in conectores:
        if inicio == 0:
            continue

        combinacion = " ".join(tokens[inicio:fin])

        if (
            tokens[inicio] in _CONECTORES_SIMPLES
            or combinacion in _CONECTORES_MULTIPALABRA
        ):
            if any(posicion >= fin for posicion in posiciones_verbo):
                validos.append((inicio, fin))
            continue

        if fin in posiciones_verbo:
            validos.append((inicio, fin))

    return validos


def _dividir_en_clausulas(
    conectores_validos: list[tuple[int, int]],
    cantidad_tokens: int,
) -> list[tuple[int, int]]:
    """Divide los tokens en clausulas separadas por conectores validos."""
    clausulas = []
    cursor = 0

    for inicio, fin in sorted(conectores_validos):
        if cursor < inicio:
            clausulas.append((cursor, inicio))
        cursor = max(cursor, fin)

    if cursor < cantidad_tokens:
        clausulas.append((cursor, cantidad_tokens))

    return clausulas


def _operacion_desde_clausula(
    tokens_norm: list[str],
    tokens_orig: list[str],
    inicio: int,
    fin: int,
    orden: int,
    registro: RegistroVerbos,
) -> Operacion | None:
    if inicio >= fin:
        return None

    verbo = registro.buscar_por_sinonimo(tokens_norm[inicio])

    if verbo is None:
        return None

    texto = " ".join(tokens_orig[inicio:fin])

    if fin - inicio == 1:
        return Operacion(verbo=verbo.nombre, orden=orden, texto=texto)

    valor = _limpiar_puntuacion(" ".join(tokens_orig[inicio + 1:fin]))

    return Operacion(
        verbo=verbo.nombre,
        entidad=Entidad(
            tipo=_clasificar_tipo_entidad(valor, verbo),
            valor=valor,
            normalizado=normalizar_para_busqueda(valor),
        ),
        orden=orden,
        texto=texto,
    )


def _clasificar_tipo_entidad(valor: str, verbo: Verbo) -> str:
    palabras = normalizar_para_busqueda(valor).split()

    if "proyecto" in palabras or "proyectos" in palabras:
        return TIPO_PROYECTO

    if verbo.nombre == "ejecutar" and "pruebas" in palabras:
        return TIPO_TAREA

    return verbo.tipo_entidad


def _limpiar_puntuacion(valor: str) -> str:
    return _PUNTUACION_FINAL.sub("", valor).strip()