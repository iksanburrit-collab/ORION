from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any

from servicios.calendario.contratos import EventoCalendario
from servicios.calendario.local import ProveedorCalendarioLocal
from utilidades.rutas import ruta_calendario_local


def puede_manejar_tareas(texto: str) -> bool:
    return bool(
        re.match(r"^(?:agrega tarea|nueva tarea)\s+.+$", texto)
        or texto in {"mis tareas", "tareas pendientes", "mis eventos"}
        or re.match(r"^(?:completa tarea|elimina tarea)\s+\S+$", texto)
        or re.match(r"^recuerdame\s+.+$", texto)
        or re.match(
            r"^crea evento\s+.+\s+el\s+\d{4}-\d{2}-\d{2}\s+a\s+las\s+\d{2}:\d{2}$",
            texto,
        )
    )


def procesar_tareas(
    texto: str,
    proveedor: ProveedorCalendarioLocal | None = None,
    ahora: datetime | None = None,
) -> tuple[bool, str, str, dict[str, Any] | None]:
    proveedor = proveedor or ProveedorCalendarioLocal()
    ahora = ahora or datetime.now()

    if proveedor.error_carga:
        return (
            True,
            "calendario_no_disponible",
            "No pude leer el calendario local porque su archivo JSON es invalido.",
            None,
        )

    coincidencia = re.match(r"^(?:agrega tarea|nueva tarea)\s+(.+)$", texto)
    if coincidencia:
        titulo = coincidencia.group(1).strip()
        if not titulo:
            return True, "tarea_invalida", "La tarea no puede estar vacia.", None

        evento = proveedor.crear_evento(EventoCalendario(id="", titulo=titulo))
        return True, "agregar_tarea", f"Tarea agregada: {evento.id} - {evento.titulo}", None

    if texto in {"mis tareas", "tareas pendientes"}:
        pendientes = [
            evento
            for evento in proveedor.listar_eventos("pendiente")
            if evento.tipo == "tarea"
        ]
        return True, "listar_tareas", _formatear_eventos(pendientes, "No hay tareas pendientes"), None

    coincidencia = re.match(r"^completa tarea\s+(\S+)$", texto)
    if coincidencia:
        evento = proveedor.completar_tarea(coincidencia.group(1))
        if not evento:
            return True, "completar_tarea", "No encontre esa tarea.", None
        return True, "completar_tarea", f"Tarea completada: {evento.id}", None

    coincidencia = re.match(r"^elimina tarea\s+(\S+)$", texto)
    if coincidencia:
        tarea_id = coincidencia.group(1)
        solicitud = {
            "tipo": "confirmar_tarea",
            "identificador": tarea_id,
            "accion": "eliminar_tarea",
            "datos": {"archivo": proveedor.archivo},
            "parametros": {
                "id": tarea_id,
                "archivo": proveedor.archivo,
            },
            "nivel_riesgo": "medio",
            "texto_confirmacion": f"Quieres eliminar la tarea {tarea_id}?",
        }
        return True, "solicitar_eliminar_tarea", solicitud["texto_confirmacion"], solicitud

    coincidencia = re.match(r"^recuerdame\s+(.+?)(?:\s+mañana|\s+manana)?$", texto)
    if coincidencia and texto.startswith("recuerdame "):
        titulo = coincidencia.group(1).strip()
        if not titulo:
            return True, "recordatorio_invalido", "El recordatorio no puede estar vacio.", None

        inicio = None
        if texto.endswith(" mañana") or texto.endswith(" manana"):
            inicio = (ahora + timedelta(days=1)).replace(microsecond=0).isoformat()
        elif _contiene_fecha_ambigua(texto):
            solicitud = {
                "tipo": "confirmar_fecha",
                "identificador": titulo,
                "accion": "crear_recordatorio",
                "datos": {"texto": titulo},
                "parametros": {"texto": titulo},
                "nivel_riesgo": "bajo",
                "texto_confirmacion": "Necesito una fecha mas clara para el recordatorio.",
            }
            return True, "solicitar_fecha_recordatorio", solicitud["texto_confirmacion"], solicitud

        evento = proveedor.crear_evento(
            EventoCalendario(
                id="",
                titulo=titulo,
                inicio=inicio,
                metadatos={"tipo": "recordatorio"},
            )
        )
        return True, "agregar_recordatorio", f"Recordatorio agregado: {evento.id} - {evento.titulo}", None

    coincidencia = re.match(
        r"^crea evento\s+(.+)\s+el\s+(\d{4}-\d{2}-\d{2})\s+a\s+las\s+(\d{2}:\d{2})$",
        texto,
    )
    if coincidencia:
        titulo, fecha, hora = coincidencia.groups()
        try:
            inicio_dt = datetime.fromisoformat(f"{fecha}T{hora}:00")
        except ValueError:
            return True, "evento_fecha_invalida", "La fecha del evento no es valida.", None

        fin_dt = inicio_dt + timedelta(hours=1)
        evento = proveedor.crear_evento(
            EventoCalendario(
                id="",
                titulo=titulo.strip(),
                inicio=inicio_dt.isoformat(),
                fin=fin_dt.isoformat(),
            )
        )
        return True, "crear_evento", f"Evento creado: {evento.id} - {evento.titulo}", None

    if texto == "mis eventos":
        eventos = [
            evento
            for evento in proveedor.listar_eventos("pendiente")
            if evento.tipo == "evento"
        ]
        return True, "listar_eventos", _formatear_eventos(eventos, "No hay eventos pendientes"), None

    return False, "", "", None


def confirmar_eliminar_tarea(solicitud: dict[str, Any]) -> str:
    parametros = solicitud.get("parametros", {})
    if solicitud.get("accion") != "eliminar_tarea":
        return "No pude completar esa solicitud."

    proveedor = ProveedorCalendarioLocal(
        str(parametros.get("archivo") or ruta_calendario_local())
    )
    tarea_id = str(parametros.get("id", ""))
    if str(solicitud.get("identificador", "")) != tarea_id:
        return "No pude completar esa solicitud."

    if proveedor.eliminar_evento(tarea_id):
        return f"Tarea eliminada: {tarea_id}"

    return "No encontre esa tarea."


def _formatear_eventos(eventos: list[EventoCalendario], vacio: str) -> str:
    if not eventos:
        return vacio

    return "\n".join(
        f"{evento.id}. {evento.titulo}" + (f" ({evento.inicio})" if evento.inicio else "")
        for evento in eventos
    )


def _contiene_fecha_ambigua(texto: str) -> bool:
    return any(palabra in texto for palabra in ("hoy", "luego", "despues", "pronto"))
