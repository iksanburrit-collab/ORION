from __future__ import annotations

from typing import Any, Callable


GuardarFunc = Callable[[], None]


def procesar_alias(
    texto: str,
    alias: dict[str, str],
    config: dict[str, Any],
    guardar_alias: GuardarFunc | None = None,
) -> tuple[bool, str, str]:

    if texto.startswith("aprende:"):
        try:
            contenido = texto.replace("aprende:", "", 1)
            clave, valor = contenido.split("=", 1)

            clave = clave.strip()
            valor = valor.strip()

            if not clave or not valor:
                return (
                    True,
                    "alias_invalido",
                    "Formato: aprende: comando=accion",
                )

            alias[clave] = valor

            if guardar_alias:
                guardar_alias()

            return True, "guardar_alias", "Alias guardado 👍"

        except ValueError:
            return (
                True,
                "alias_invalido",
                "Formato: aprende: comando=accion",
            )

    if texto in alias:
        return True, "ejecutar_alias", alias[texto]

    return False, "", ""