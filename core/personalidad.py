"""
Módulo de personalidad de ORION.
"""

import random
from typing import Any


def responder_personalidad(
    texto: str,
    config: dict[str, Any],
) -> str:
    """
    Adapta una respuesta al modo de personalidad activo.

    No imprime nada. Devuelve el texto final.
    """

    modo = config.get("modo", "normal")

    if modo == "ironman":
        return random.choice([
            f"Señor, {texto}",
            f"A sus órdenes señor. {texto}",
            f"Sistema ORION activo. {texto}",
            f"Procesado señor. {texto}",
        ])

    if modo == "chill":
        return random.choice([
            f"{texto} 😎",
            f"Tranqui → {texto}",
            f"Todo cool 😄 {texto}",
            f"Va 😎 {texto}",
        ])

    if modo == "serio":
        return random.choice([
            texto,
            f"Confirmado. {texto}",
            f"Ejecutando. {texto}",
        ])

    return texto