from __future__ import annotations

from typing import Callable


GuardarFunc = Callable[[], None]


def procesar_notas(
    texto: str,
    notas: list[str],
    guardar_notas: GuardarFunc | None = None,
) -> tuple[bool, str, str]:
    """
    Procesa comandos relacionados con notas.

    Devuelve:
    - procesado
    - accion
    - respuesta
    """

    if texto.startswith("recuerda "):
        nota = texto.replace("recuerda ", "", 1).strip()

        if not nota:
            return True, "nota_invalida", "La nota no puede estar vacía."

        notas.append(nota)

        if guardar_notas:
            guardar_notas()

        return True, "guardar_nota", "Nota guardada 👍"

    if texto == "notas":
        if not notas:
            return True, "listar_notas", "No hay notas"

        lineas = ["NOTAS", ""]

        lineas.extend(
            f"{indice}. {nota}"
            for indice, nota in enumerate(notas, start=1)
        )

        return True, "listar_notas", "\n".join(lineas)

    if texto == "borrar notas":
        notas.clear()

        if guardar_notas:
            guardar_notas()

        return True, "borrar_notas", "Notas eliminadas"

    return False, "", ""