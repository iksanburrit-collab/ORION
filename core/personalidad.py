"""
Módulo de personalidad de ORION.
"""

import random


def responder_personalidad(texto, config):

    modo = config.get(
        "modo",
        "normal"
    )

    if modo == "ironman":

        print(
            random.choice([
                f"Señor, {texto}",
                f"A sus órdenes señor. {texto}",
                f"Sistema ORION activo. {texto}",
                f"Procesado señor. {texto}"
            ])
        )

    elif modo == "chill":

        print(
            random.choice([
                f"{texto} 😎",
                f"Tranqui → {texto}",
                f"Todo cool 😄 {texto}",
                f"Va 😎 {texto}"
            ])
        )

    elif modo == "serio":

        print(
            random.choice([
                texto,
                f"Confirmado. {texto}",
                f"Ejecutando. {texto}"
            ])
        )

    else:

        print(texto)
