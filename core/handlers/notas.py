from __future__ import annotations

import re
from typing import Any, Callable

from servicios.notas import RepositorioNotas
from utilidades.rutas import ruta_notas


GuardarFunc = Callable[[], None]


def puede_manejar_notas(texto: str) -> bool:
    return bool(
        re.match(r"^(?:anota|recuerda)\s+.+$", texto)
        or texto in {"notas", "mis notas", "lista notas", "borrar notas"}
        or re.match(r"^(?:borra|elimina) nota\s+\S+$", texto)
    )


def procesar_notas(
    texto: str,
    notas: list[Any],
    guardar_notas: GuardarFunc | None = None,
    archivo_notas: str | None = None,
) -> tuple[bool, str, str, dict[str, Any] | None]:
    repositorio = RepositorioNotas(
        archivo=archivo_notas,
        datos=notas,
        guardar_externo=guardar_notas,
    )

    coincidencia = re.match(r"^(?:anota|recuerda)\s+(.+)$", texto)
    if coincidencia:
        contenido = coincidencia.group(1).strip()
        if not contenido:
            return True, "nota_invalida", "La nota no puede estar vacia.", None
        nota = repositorio.crear(contenido)
        return True, "guardar_nota", f"Nota guardada: {nota.id}", None

    if texto in {"notas", "mis notas", "lista notas"}:
        activas = repositorio.listar_activas()
        if not activas:
            return True, "listar_notas", "No hay notas activas", None
        lineas = ["NOTAS", ""]
        lineas.extend(f"{nota.id}. {nota.contenido}" for nota in activas)
        return True, "listar_notas", "\n".join(lineas), None

    coincidencia = re.match(r"^(?:borra|elimina) nota\s+(\S+)$", texto)
    if coincidencia:
        nota_id = coincidencia.group(1)
        if not repositorio.buscar(nota_id, estado="activa"):
            return (
                True,
                "nota_no_encontrada",
                "No encontre esa nota. Usa \"mis notas\" para ver sus IDs.",
                None,
            )
        solicitud = _solicitud_eliminar_nota(nota_id, repositorio.archivo)
        return True, "solicitar_eliminar_nota", solicitud["texto_confirmacion"], solicitud

    if texto == "borrar notas":
        if not repositorio.listar_activas():
            return True, "borrar_notas", "No hay notas activas", None
        solicitud = _solicitud_eliminar_nota("todas", repositorio.archivo)
        return True, "solicitar_eliminar_notas", solicitud["texto_confirmacion"], solicitud

    return False, "", "", None


def confirmar_eliminacion_nota(solicitud: dict[str, Any]) -> str:
    datos = solicitud.get("datos", {})
    archivo = str(datos.get("archivo") or ruta_notas())
    repositorio = RepositorioNotas(archivo=archivo)
    identificador = str(solicitud.get("identificador", ""))

    if solicitud.get("accion") == "eliminar_todas_notas" and identificador == "todas":
        cantidad = repositorio.eliminar_todas()
        return f"Notas eliminadas: {cantidad}" if cantidad else "No hay notas activas"

    if solicitud.get("accion") == "eliminar_nota" and repositorio.eliminar(identificador):
        return f"Nota eliminada: {identificador}"

    return "No encontre esa nota. Usa \"mis notas\" para ver sus IDs."


def _solicitud_eliminar_nota(nota_id: str, archivo: str) -> dict[str, Any]:
    todas = nota_id == "todas"
    return {
        "tipo": "confirmar_nota",
        "identificador": nota_id,
        "accion": "eliminar_todas_notas" if todas else "eliminar_nota",
        "datos": {"archivo": archivo},
        "nivel_riesgo": "medio",
        "texto_confirmacion": (
            "Quieres eliminar todas las notas activas?"
            if todas
            else f"Quieres eliminar la nota {nota_id}?"
        ),
    }
