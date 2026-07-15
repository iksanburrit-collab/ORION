from __future__ import annotations

from servicios.sistema.contratos import AccionPC


class RegistroCapacidades:
    def __init__(self) -> None:
        self._acciones: dict[str, AccionPC] = {}

    def registrar(self, accion: AccionPC) -> None:
        self._acciones[accion.nombre] = accion

    def obtener(self, nombre: str) -> AccionPC | None:
        return self._acciones.get(nombre)

    def listar(self) -> list[AccionPC]:
        return list(self._acciones.values())
