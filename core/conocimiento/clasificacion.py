from __future__ import annotations

import re
from typing import Any

from core.conocimiento.terminos import (
    ALIAS_GUSTOS,
    CATEGORIAS_APRENDIZAJE,
    CATEGORIAS_GUSTOS,
    CATEGORIAS_GUSTOS_MEMORIA,
    CATEGORIAS_HERRAMIENTAS,
    ENTIDADES_CATEGORIAS_GUSTOS,
    PALABRAS_CLAVE_GUSTOS,
    PATRONES_GUSTOS,
    ClasificacionGusto,
)
from core.conocimiento.normalizacion import (
    _formatear_desconocido,
    canonizar_entidad,
    limpiar_valor,
    normalizar_para_busqueda,
)


def clasificar_gusto(
    valor: str,
    texto_original: str = "",
    categoria_contexto: str | None = None,
) -> ClasificacionGusto:
    valor_limpio = canonizar_entidad(limpiar_valor(valor))
    categoria_alias = ENTIDADES_CATEGORIAS_GUSTOS.get(
        normalizar_para_busqueda(valor_limpio)
    )

    if (
        categoria_contexto is None
        and texto_original in CATEGORIAS_GUSTOS_MEMORIA
    ):
        categoria_contexto = texto_original
        texto_original = valor_limpio

    texto_original = texto_original or valor_limpio
    categoria_contexto = _normalizar_categoria_gusto(categoria_contexto)

    if categoria_alias:
        return ClasificacionGusto(
            categoria_alias,
            valor_limpio,
            1.0,
            ("alias_entidad",),
        )

    if categoria_contexto in CATEGORIAS_GUSTOS_MEMORIA:
        return ClasificacionGusto(
            categoria_contexto,
            _canonizar_valor(
                valor_limpio,
                CATEGORIAS_GUSTOS.get(categoria_contexto, set()),
            ),
            1.0,
            ("contexto_explicito",),
        )

    categoria_detectada = _clasificar_por_diccionario(
        valor_limpio,
        CATEGORIAS_GUSTOS
    )

    if categoria_detectada:
        categoria, valor_canonico = categoria_detectada
        return ClasificacionGusto(
            categoria,
            valor_canonico,
            1.0,
            ("entidad_conocida",),
        )

    return _clasificar_gusto_por_reglas(valor_limpio, texto_original)


def _clasificar_gusto_por_reglas(
    valor: str,
    texto_original: str,
) -> ClasificacionGusto:
    valor_normalizado = normalizar_para_busqueda(valor)
    texto_normalizado = normalizar_para_busqueda(texto_original)
    texto_combinado = f"{texto_normalizado} {valor_normalizado}".strip()
    puntuaciones: dict[str, float] = {}
    razones: dict[str, list[str]] = {}

    def sumar(categoria: str, puntos: float, razon: str) -> None:
        puntuaciones[categoria] = puntuaciones.get(categoria, 0.0) + puntos
        razones.setdefault(categoria, []).append(razon)

    for alias, categoria in ALIAS_GUSTOS.items():
        alias_normalizado = normalizar_para_busqueda(alias)

        if _contiene_termino(texto_combinado, alias_normalizado):
            sumar(categoria, 1.2, f"alias:{alias_normalizado}")

    for categoria, palabras in PALABRAS_CLAVE_GUSTOS.items():
        for palabra in palabras:
            palabra_normalizada = normalizar_para_busqueda(palabra)

            if _contiene_termino(valor_normalizado, palabra_normalizada):
                sumar(categoria, 1.1, f"valor:{palabra_normalizada}")
            elif _contiene_termino(texto_normalizado, palabra_normalizada):
                sumar(categoria, 0.7, f"contexto:{palabra_normalizada}")

    for categoria, patrones in PATRONES_GUSTOS.items():
        for patron in patrones:
            if re.search(patron, valor_normalizado):
                sumar(categoria, 1.05, f"patron:{patron}")

    _sumar_por_contexto_frase(texto_normalizado, sumar)

    if not puntuaciones:
        return ClasificacionGusto(
            "otros",
            _formatear_desconocido(valor),
            0.25,
            ("sin_senales_suficientes",),
        )

    ordenadas = sorted(
        puntuaciones.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    categoria, puntuacion = ordenadas[0]
    segunda = ordenadas[1][1] if len(ordenadas) > 1 else 0.0

    if puntuacion < 1.0 or puntuacion - segunda < 0.35:
        return ClasificacionGusto(
            "otros",
            _formatear_desconocido(valor),
            min(0.5, puntuacion / 3.0),
            tuple(razones.get(categoria, ("clasificacion_ambigua",))),
        )

    confianza = min(0.9, 0.45 + puntuacion / 4.0)
    return ClasificacionGusto(
        categoria,
        _formatear_desconocido(valor),
        confianza,
        tuple(razones.get(categoria, ())),
    )


def _sumar_por_contexto_frase(
    texto_normalizado: str,
    sumar: Any,
) -> None:
    reglas = (
        ("videojuegos", ("juego", "juegos", "videojuego", "videojuegos")),
        ("deportes", ("deporte", "deportes", "jugar al", "practicar")),
        ("comida", ("comer", "comida", "platillo", "postre")),
        ("musica", ("escuchar", "musica", "cancion", "banda", "artista")),
        ("tecnologia", ("programar", "codigo", "software", "tecnologia")),
        ("peliculas", ("ver peliculas", "cine", "pelicula")),
        ("series", ("ver series", "serie", "anime")),
    )

    for categoria, pistas in reglas:
        for pista in pistas:
            if _contiene_termino(texto_normalizado, pista):
                sumar(categoria, 0.9, f"frase:{pista}")


def _normalizar_categoria_gusto(categoria: str | None) -> str | None:
    if not categoria:
        return None

    categoria_normalizada = normalizar_para_busqueda(categoria)
    return ALIAS_GUSTOS.get(categoria_normalizada, categoria_normalizada)


def _contiene_termino(texto: str, termino: str) -> bool:
    if not texto or not termino:
        return False

    if " " in termino:
        return termino in texto

    return bool(re.search(rf"\b{re.escape(termino)}\b", texto))


def clasificar_aprendizaje(valor: str) -> tuple[str, str]:
    valor_limpio = canonizar_entidad(limpiar_valor(valor))
    categoria_detectada = _clasificar_por_diccionario(
        valor_limpio,
        CATEGORIAS_APRENDIZAJE
    )

    if categoria_detectada:
        return categoria_detectada

    return "otros", _formatear_desconocido(valor_limpio)


def clasificar_herramienta(valor: str) -> tuple[str, str]:
    valor_limpio = canonizar_entidad(limpiar_valor(valor))
    categoria_detectada = _clasificar_por_diccionario(
        valor_limpio,
        CATEGORIAS_HERRAMIENTAS
    )

    if categoria_detectada:
        return categoria_detectada

    return "otros", _formatear_desconocido(valor_limpio)


def _clasificar_por_diccionario(
    valor: str,
    categorias: dict[str, set[str]]
) -> tuple[str, str] | None:
    valor_normalizado = normalizar_para_busqueda(valor)

    for categoria, terminos in categorias.items():
        for termino in terminos:
            termino_normalizado = normalizar_para_busqueda(termino)

            if (
                valor_normalizado == termino_normalizado
                or re.search(
                    rf"\b{re.escape(termino_normalizado)}\b",
                    valor_normalizado
                )
            ):
                return categoria, termino

    return None


def _canonizar_valor(valor: str, terminos: set[str]) -> str:
    valor_normalizado = normalizar_para_busqueda(valor)

    for termino in terminos:
        if normalizar_para_busqueda(termino) == valor_normalizado:
            return termino

    return _formatear_desconocido(valor)

