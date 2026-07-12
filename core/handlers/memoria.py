from __future__ import annotations

from typing import Any

from core.memoria import obtener_ultimo_comando, obtener_ultimo_gusto


def procesar_memoria(texto: str, memoria: dict[str, Any]) -> tuple[bool, str, str]:
    if "que hice" in texto:
        ultimo = obtener_ultimo_comando(memoria)
        respuesta = (
            f"La última orden fue: {ultimo}"
            if ultimo
            else "No recuerdo nada todavía"
        )
        return True, "recordar_ultimo_comando", respuesta

    if "que me gusta" in texto:
        gusto = obtener_ultimo_gusto(memoria)
        respuesta = (
            f"Recuerdo esto: {gusto}"
            if gusto
            else "Todavía no sé tus gustos"
        )
        return True, "recordar_gusto", respuesta

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
