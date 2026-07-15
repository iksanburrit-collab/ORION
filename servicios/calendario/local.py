from __future__ import annotations

from typing import Any

from servicios.calendario.contratos import EventoCalendario, fecha_iso
from utilidades.archivos import cargar_json, guardar_json
from utilidades.rutas import ruta_calendario_local


class ProveedorCalendarioLocal:
    proveedor = "local"

    def __init__(self, archivo: str | None = None) -> None:
        self.archivo = archivo or ruta_calendario_local()
        self.error_carga: str | None = None
        self._proximo_id = 1
        self._eventos = self._cargar()

    def crear_evento(self, evento: EventoCalendario) -> EventoCalendario:
        if not evento.id:
            evento.id = self._siguiente_id()

        evento.proveedor = self.proveedor
        evento.actualizado = fecha_iso()
        self._eventos.append(evento)
        self._guardar()
        return evento

    def listar_eventos(self, estado: str | None = None) -> list[EventoCalendario]:
        eventos = list(self._eventos)

        if estado:
            eventos = [evento for evento in eventos if evento.estado == estado]

        return eventos

    def actualizar_evento(
        self,
        evento_id: str,
        cambios: dict[str, Any],
    ) -> EventoCalendario | None:
        evento = self._buscar(evento_id)

        if evento is None:
            return None

        for clave in (
            "titulo",
            "descripcion",
            "inicio",
            "fin",
            "estado",
            "proveedor_id",
        ):
            if clave in cambios:
                setattr(evento, clave, cambios[clave])

        evento.actualizado = fecha_iso()
        evento.sincronizacion.estado = "solo_local"
        self._guardar()
        return evento

    def eliminar_evento(self, evento_id: str) -> bool:
        longitud = len(self._eventos)
        self._eventos = [
            evento for evento in self._eventos if evento.id != evento_id
        ]

        if len(self._eventos) == longitud:
            return False

        self._guardar()
        return True

    def completar_tarea(self, evento_id: str) -> EventoCalendario | None:
        return self.actualizar_evento(evento_id, {"estado": "completada"})

    def sincronizar(self) -> dict[str, Any]:
        return {
            "proveedor": self.proveedor,
            "estado": "sin_adaptador_remoto",
            "eventos": len(self._eventos),
        }

    def _cargar(self) -> list[EventoCalendario]:
        resultado = cargar_json(self.archivo, {"eventos": []})
        self.error_carga = resultado.error
        datos = resultado.datos

        if isinstance(datos, list):
            datos = self._migrar_lista_antigua(datos)

        if not isinstance(datos, dict):
            datos = {"eventos": []}

        eventos = []
        for item in datos.get("eventos", []):
            if not isinstance(item, dict):
                continue

            evento = EventoCalendario.desde_dict(item)
            if evento.id and evento.titulo:
                eventos.append(evento)

        derivados = [
            int(evento.id.removeprefix("local-"))
            for evento in eventos
            if evento.id.startswith("local-")
            and evento.id.removeprefix("local-").isdigit()
        ]
        siguiente_guardado = datos.get("siguiente_id", 1)
        try:
            siguiente_guardado = int(siguiente_guardado)
        except (TypeError, ValueError):
            siguiente_guardado = 1
        self._proximo_id = max(siguiente_guardado, max(derivados, default=0) + 1)

        return eventos

    def _guardar(self) -> None:
        if self.error_carga:
            raise ValueError("El calendario local contiene JSON invalido; no se sobrescribio.")

        guardar_json(
            self.archivo,
            {
                "version": 1,
                "proveedor": self.proveedor,
                "siguiente_id": self._proximo_id,
                "eventos": [evento.como_dict() for evento in self._eventos],
            },
        )

    def _siguiente_id(self) -> str:
        usados = {evento.id for evento in self._eventos}
        while f"local-{self._proximo_id}" in usados:
            self._proximo_id += 1

        evento_id = f"local-{self._proximo_id}"
        self._proximo_id += 1
        return evento_id

    def _buscar(self, evento_id: str) -> EventoCalendario | None:
        for evento in self._eventos:
            if evento.id == evento_id:
                return evento

        return None

    def _migrar_lista_antigua(self, datos: list[Any]) -> dict[str, Any]:
        eventos = []

        for indice, item in enumerate(datos, start=1):
            if isinstance(item, str) and item.strip():
                eventos.append({
                    "id": f"local-{indice}",
                    "titulo": item.strip(),
                    "estado": "pendiente",
                    "proveedor": self.proveedor,
                    "sincronizacion": {
                        "estado": "solo_local",
                        "ultima_sincronizacion": None,
                        "conflicto": False,
                    },
                })

        return {"version": 1, "proveedor": self.proveedor, "eventos": eventos}
