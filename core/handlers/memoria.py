from __future__ import annotations

import re
from typing import Any

from core.conocimiento import normalizar_para_busqueda
from core.memoria import (
    cambiar_objetivo,
    consultar_aprendizaje,
    consultar_gustos,
    consultar_objetivos,
    consultar_proyectos,
    consultar_resumen_personal,
    guardar_memoria,
    obtener_ultimo_comando,
    olvidar_aprendizaje,
    olvidar_gusto,
)


def procesar_memoria(texto: str, memoria: dict[str, Any]) -> tuple[bool, str, str]:
    correccion = _procesar_correccion(texto, memoria)

    if correccion[0]:
        return correccion

    consulta = _procesar_consulta(texto, memoria)

    if consulta[0]:
        return consulta

    if "que hice" in texto:
        ultimo = obtener_ultimo_comando(memoria)
        respuesta = (
            f"La ultima orden fue: {ultimo}"
            if ultimo
            else "No recuerdo nada todavia"
        )
        return True, "recordar_ultimo_comando", respuesta

    if "que recuerdas" in texto:
        return (
            True,
            "contar_recuerdos",
            f"Tengo {len(memoria['historial'])} recuerdos recientes",
        )

    if "historial" in texto:
        historial = memoria["historial"]

        if len(historial) == 0:
            return True, "mostrar_historial", "No tengo historial"

        return (
            True,
            "mostrar_historial",
            "\n".join(f"- {entrada}" for entrada in historial[-10:]),
        )

    return False, "", ""


def _procesar_consulta(
    texto: str,
    memoria: dict[str, Any]
) -> tuple[bool, str, str]:
    consulta = normalizar_para_busqueda(texto)

    if consulta == "que sabes de mi":
        return (
            True,
            "consultar_resumen_personal",
            consultar_resumen_personal(memoria),
        )

    if consulta in {"que me gusta", "que gustos tengo"}:
        return True, "listar_gustos", _listar_gustos(memoria)

    if consulta == "que videojuegos me gustan":
        return (
            True,
            "consultar_videojuegos",
            _respuesta_consulta(
                "Tus videojuegos guardados",
                consultar_gustos(memoria, "videojuegos"),
            ),
        )

    if consulta == "que deportes me gustan":
        return (
            True,
            "consultar_deportes",
            _respuesta_consulta(
                "Tus deportes guardados",
                consultar_gustos(memoria, "deportes"),
            ),
        )

    if consulta in {"que musica me gusta", "que musica me gustan"}:
        return (
            True,
            "consultar_musica",
            _respuesta_consulta(
                "Tu musica guardada",
                consultar_gustos(memoria, "musica"),
            ),
        )

    if consulta in {"que comidas me gustan", "que comida me gusta"}:
        return (
            True,
            "consultar_comida",
            _respuesta_consulta(
                "Tus comidas guardadas",
                consultar_gustos(memoria, "comida"),
            ),
        )

    if consulta == "que estoy aprendiendo":
        return (
            True,
            "consultar_aprendizaje",
            _respuesta_consulta(
                "Estas aprendiendo",
                consultar_aprendizaje(memoria),
            ),
        )

    if consulta == "cuales son mis objetivos":
        return (
            True,
            "consultar_objetivos",
            _respuesta_consulta(
                "Tus objetivos",
                consultar_objetivos(memoria),
            ),
        )

    if consulta == "que proyectos tengo":
        return (
            True,
            "consultar_proyectos",
            _respuesta_consulta(
                "Tus proyectos",
                consultar_proyectos(memoria),
            ),
        )

    return False, "", ""


def _procesar_correccion(
    texto: str,
    memoria: dict[str, Any]
) -> tuple[bool, str, str]:
    coincidencia = re.match(
        r"^(?:ya\s+no\s+me\s+gusta|olvida\s+que\s+me\s+gusta)\s+(.+)$",
        texto,
    )

    if coincidencia:
        valor = coincidencia.group(1).strip()
        olvidado = olvidar_gusto(memoria, valor)
        guardar_memoria(memoria)

        if olvidado:
            return True, "olvidar_gusto", f"Listo, olvide que te gusta {valor}"

        return True, "olvidar_gusto", f"No tenia guardado ese gusto: {valor}"

    coincidencia = re.match(
        r"^olvida\s+que\s+estoy\s+aprendiendo\s+(.+)$",
        texto,
    )

    if coincidencia:
        valor = coincidencia.group(1).strip()
        olvidado = olvidar_aprendizaje(memoria, valor)
        guardar_memoria(memoria)

        if olvidado:
            return (
                True,
                "olvidar_aprendizaje",
                f"Listo, olvide que estas aprendiendo {valor}",
            )

        return (
            True,
            "olvidar_aprendizaje",
            f"No tenia guardado ese aprendizaje: {valor}",
        )

    coincidencia = re.match(r"^cambia\s+mi\s+objetivo\s+a\s+(.+)$", texto)

    if coincidencia:
        valor = coincidencia.group(1).strip()

        if cambiar_objetivo(memoria, valor):
            guardar_memoria(memoria)
            return True, "cambiar_objetivo", f"Objetivo actualizado: {valor}"

        return True, "cambiar_objetivo", "No pude guardar ese objetivo"

    return False, "", ""


def _respuesta_consulta(titulo: str, detalle: str) -> str:
    if detalle.startswith("No tengo"):
        return detalle

    return f"{titulo}: {detalle}"


def _listar_gustos(memoria: dict[str, Any]) -> str:
    gustos = memoria.get("usuario", {}).get("gustos", {})
    partes = []

    for categoria, valores in gustos.items():
        if valores:
            partes.append(
                f"{categoria}: {', '.join(valores)}"
            )

    if partes:
        return "Tus gustos:\n" + "\n".join(partes)

    return "Todavia no se tus gustos"
