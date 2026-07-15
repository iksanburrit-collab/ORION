from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


def fecha_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class SincronizacionCalendario:
    estado: str = "solo_local"
    ultima_sincronizacion: str | None = None
    conflicto: bool = False

    def como_dict(self) -> dict[str, Any]:
        return {
            "estado": self.estado,
            "ultima_sincronizacion": self.ultima_sincronizacion,
            "conflicto": self.conflicto,
        }


@dataclass
class EventoCalendario:
    id: str
    titulo: str
    descripcion: str = ""
    inicio: str | None = None
    fin: str | None = None
    estado: str = "pendiente"
    proveedor: str = "local"
    proveedor_id: str | None = None
    creado: str = field(default_factory=fecha_iso)
    actualizado: str = field(default_factory=fecha_iso)
    metadatos: dict[str, Any] = field(default_factory=dict)
    sincronizacion: SincronizacionCalendario = field(
        default_factory=SincronizacionCalendario
    )

    @property
    def tipo(self) -> str:
        tipo_explicito = self.metadatos.get("tipo")
        if tipo_explicito in {"tarea", "recordatorio", "evento"}:
            return str(tipo_explicito)

        if self.inicio and self.fin:
            return "evento"
        if self.inicio:
            return "recordatorio"
        return "tarea"

    def como_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "inicio": self.inicio,
            "fin": self.fin,
            "estado": self.estado,
            "proveedor": self.proveedor,
            "proveedor_id": self.proveedor_id,
            "creado": self.creado,
            "actualizado": self.actualizado,
            "metadatos": self.metadatos,
            "sincronizacion": self.sincronizacion.como_dict(),
        }

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> "EventoCalendario":
        sync = datos.get("sincronizacion", {})
        if not isinstance(sync, dict):
            sync = {}

        return cls(
            id=str(datos.get("id", "")),
            titulo=str(datos.get("titulo", "")).strip(),
            descripcion=str(datos.get("descripcion", "") or ""),
            inicio=datos.get("inicio"),
            fin=datos.get("fin"),
            estado=str(datos.get("estado", "pendiente")),
            proveedor=str(datos.get("proveedor", "local")),
            proveedor_id=datos.get("proveedor_id"),
            creado=str(datos.get("creado") or fecha_iso()),
            actualizado=str(datos.get("actualizado") or fecha_iso()),
            metadatos=datos.get("metadatos", {})
            if isinstance(datos.get("metadatos"), dict)
            else {},
            sincronizacion=SincronizacionCalendario(
                estado=str(sync.get("estado", "solo_local")),
                ultima_sincronizacion=sync.get("ultima_sincronizacion"),
                conflicto=bool(sync.get("conflicto", False)),
            ),
        )


class ProveedorCalendario(Protocol):
    def crear_evento(self, evento: EventoCalendario) -> EventoCalendario:
        ...

    def listar_eventos(self, estado: str | None = None) -> list[EventoCalendario]:
        ...

    def actualizar_evento(self, evento_id: str, cambios: dict[str, Any]) -> EventoCalendario | None:
        ...

    def eliminar_evento(self, evento_id: str) -> bool:
        ...

    def completar_tarea(self, evento_id: str) -> EventoCalendario | None:
        ...

    def sincronizar(self) -> dict[str, Any]:
        ...
