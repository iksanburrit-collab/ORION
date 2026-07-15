from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from core.conocimiento import normalizar_para_busqueda
from servicios.calendario.contratos import EventoCalendario
from servicios.calendario.local import ProveedorCalendarioLocal


GuardarFunc = Callable[[], None]
MIGRACION_RECORDATORIOS = "recordatorios_legacy_v1"


def migrar_recordatorios_legacy(
    recordatorios: list[Any],
    proveedor: ProveedorCalendarioLocal | None = None,
    guardar_recordatorios: GuardarFunc | None = None,
) -> int:
    if not isinstance(recordatorios, list) or not recordatorios:
        return 0

    proveedor = proveedor or ProveedorCalendarioLocal()
    if proveedor.error_carga:
        return 0

    eventos = proveedor.listar_eventos()
    ids_migrados = {
        str(evento.metadatos.get("migracion_id", ""))
        for evento in eventos
        if evento.metadatos.get("migracion") == MIGRACION_RECORDATORIOS
    }
    claves_legacy = {
        _clave_legacy_existente(evento)
        for evento in eventos
        if evento.metadatos.get("origen") == "legacy"
    }
    migrados = 0
    pendientes = []

    for item in list(recordatorios):
        titulo, inicio = _datos_legacy(item)
        if not titulo:
            pendientes.append(item)
            continue

        migracion_id = _id_migracion(item)
        clave = (normalizar_para_busqueda(titulo), str(inicio or ""))
        if migracion_id in ids_migrados or clave in claves_legacy:
            continue

        proveedor.crear_evento(
            EventoCalendario(
                id="",
                titulo=titulo,
                inicio=inicio,
                metadatos={
                    "tipo": "recordatorio",
                    "origen": "legacy",
                    "migracion": MIGRACION_RECORDATORIOS,
                    "migracion_id": migracion_id,
                },
            )
        )
        ids_migrados.add(migracion_id)
        claves_legacy.add(clave)
        migrados += 1

    cambio_origen = pendientes != recordatorios
    if cambio_origen:
        recordatorios[:] = pendientes
        if guardar_recordatorios:
            guardar_recordatorios()

    return migrados


def _datos_legacy(item: Any) -> tuple[str, str | None]:
    if isinstance(item, str):
        return item.strip(), None

    if isinstance(item, dict):
        titulo = ""
        for clave in ("titulo", "texto", "recordatorio"):
            valor = item.get(clave)
            if isinstance(valor, str) and valor.strip():
                titulo = valor.strip()
                break
        inicio = item.get("inicio", item.get("fecha"))
        return titulo, str(inicio) if inicio else None

    return "", None


def _id_migracion(item: Any) -> str:
    serializado = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
    resumen = hashlib.sha256(serializado.encode("utf-8")).hexdigest()[:16]
    return f"legacy-recordatorio-{resumen}"


def _clave_legacy_existente(evento: EventoCalendario) -> tuple[str, str]:
    return normalizar_para_busqueda(evento.titulo), str(evento.inicio or "")
