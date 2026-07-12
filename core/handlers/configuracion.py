from __future__ import annotations

from typing import Any, Callable


GuardarFunc = Callable[[], None]


def procesar_configuracion(
    texto: str,
    config: dict[str, Any],
    guardar_config: GuardarFunc | None = None,
) -> tuple[bool, str, str]:

    modos = ["normal", "ironman", "serio", "chill"]

    if texto == "modo":
        modo_actual = config.get("modo", "normal")

        return (
            True,
            "mostrar_modo",
            f"Modo actual: {modo_actual}",
        )

    if texto.startswith("modo "):
        nuevo = texto.replace("modo ", "", 1).strip()

        if nuevo not in modos:
            disponibles = ", ".join(modos)

            return (
                True,
                "modo_invalido",
                f"Modos disponibles: {disponibles}",
            )

        config["modo"] = nuevo

        if guardar_config:
            guardar_config()

        return (
            True,
            "cambiar_modo",
            f"Modo {nuevo} activado",
        )

    return False, "", ""