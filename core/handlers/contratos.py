from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ResultadoCerebro:
    texto: str
    intencion: str
    accion: str = ""
    respuesta: str = ""
    salir: bool = False
    solicitud: str | dict[str, Any] | None = None
    solicitud_pendiente: dict[str, Any] | None = None
    conocimiento: Any | None = None
    debug: dict[str, Any] | None = None

    def como_dict(self) -> dict[str, Any]:
        return {
            "texto": self.texto,
            "intencion": self.intencion,
            "accion": self.accion,
            "respuesta": self.respuesta,
            "salir": self.salir,
            "solicitud": self.solicitud,
            "solicitud_pendiente": self.solicitud_pendiente,
            "conocimiento": self.conocimiento,
            "debug": self.debug,
        }