from __future__ import annotations

import re
from typing import Any

from core.conocimiento import normalizar_para_busqueda
from core.memoria import (
    buscar_memoria,
    cambiar_objetivo,
    consultar_aprendizaje,
    consultar_gustos,
    listar_memorias_activas,
    listar_memorias_olvidadas,
    consultar_objetivos,
    consultar_proyectos,
    consultar_resumen_personal,
    eliminar_memoria,
    guardar_memoria,
    obtener_ultimo_comando,
    olvidar_aprendizaje,
    olvidar_gusto,
    olvidar_memoria,
)


def puede_manejar_accion_memoria(texto: str) -> bool:
    return bool(
        re.match(r"^olvida memoria\s+\S+$", texto)
        or re.match(r"^(?:borra|elimina) memoria\s+\S+$", texto)
    )


def procesar_accion_memoria(
    texto: str,
    memoria: dict[str, Any],
) -> tuple[bool, str, str, dict[str, Any] | None]:
    coincidencia = re.match(r"^olvida memoria\s+(\S+)$", texto)
    accion = "olvidar_memoria"
    estado = "olvidada"

    if not coincidencia:
        coincidencia = re.match(r"^(?:borra|elimina) memoria\s+(\S+)$", texto)
        accion = "eliminar_memoria"
        estado = "eliminada"

    if not coincidencia:
        return False, "", "", None

    memoria_id = coincidencia.group(1)
    registro = buscar_memoria(memoria, memoria_id)
    if not registro or registro.get("estado") == "eliminada":
        return (
            True,
            "memoria_no_encontrada",
            "No encontre esa memoria. Usa \"mis memorias\" para ver sus IDs.",
            None,
        )
    if estado == "olvidada" and registro.get("estado") != "activa":
        return True, "memoria_no_activa", "Esa memoria ya no esta activa.", None

    solicitud = {
        "tipo": "confirmar_estado_memoria",
        "identificador": memoria_id,
        "accion": accion,
        "datos": {"estado": estado},
        "nivel_riesgo": "medio",
        "texto_confirmacion": (
            f"Quieres olvidar la memoria {memoria_id}?"
            if estado == "olvidada"
            else f"Quieres eliminar la memoria {memoria_id}?"
        ),
    }
    return True, f"solicitar_{accion}", solicitud["texto_confirmacion"], solicitud


def confirmar_accion_memoria(
    solicitud: dict[str, Any],
    memoria: dict[str, Any],
) -> str:
    memoria_id = str(solicitud.get("identificador", ""))
    accion = str(solicitud.get("accion", ""))

    if accion == "olvidar_memoria":
        cambiado = olvidar_memoria(memoria, memoria_id)
        mensaje = f"Memoria olvidada: {memoria_id}"
    elif accion == "eliminar_memoria":
        cambiado = eliminar_memoria(memoria, memoria_id)
        mensaje = f"Memoria eliminada: {memoria_id}"
    else:
        return "No pude completar esa solicitud."

    if cambiado:
        guardar_memoria(memoria)
        return mensaje
    return "No encontre una memoria compatible con esa solicitud."


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

    if consulta == "mis memorias":
        memorias = listar_memorias_activas(memoria)
        return True, "listar_memorias_activas", _formatear_memorias(
            memorias,
            "No tengo memorias activas",
        )

    if consulta == "memorias olvidadas":
        memorias = listar_memorias_olvidadas(memoria)
        return True, "listar_memorias_olvidadas", _formatear_memorias(
            memorias,
            "No tengo memorias olvidadas",
        )

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


def _formatear_memorias(
    memorias: list[dict[str, Any]],
    vacio: str,
) -> str:
    if not memorias:
        return vacio

    return "\n".join(
        f"- [{memoria.get('id', 'sin-id')}] "
        f"{memoria.get('tipo', 'memoria')}: {memoria.get('contenido', '')}"
        for memoria in memorias
    )
    eliminar_memoria,
