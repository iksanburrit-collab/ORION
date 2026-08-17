from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.planificador.contratos import Paso


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
    acciones: tuple[Paso, ...] = ()
    respuestas: tuple[str, ...] = ()
    reconocido: bool = False

    def agregar_accion(self, paso: Paso, respuesta: str = "") -> None:
        """Anade una accion al resultado manteniendo el orden.

        La respuesta de cada accion se conserva por separado para que la
        respuesta compuesta no pierda informacion.
        """
        self.acciones = self.acciones + (paso,)
        if respuesta:
            self.respuestas = self.respuestas + (respuesta,)

    def respuesta_compuesta(self, separador: str = "\n") -> str:
        """Respuesta que agrega el resultado de todas las acciones.

        Si no hay respuestas por accion, devuelve la respuesta unica
        (compatibilidad con el contrato anterior).
        """
        if self.respuestas:
            return separador.join(
                respuesta for respuesta in self.respuestas if respuesta
            )
        return self.respuesta

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
            "acciones": [_paso_como_dict(paso) for paso in self.acciones],
            "respuestas": self.respuestas,
            "reconocido": self.reconocido,
        }


def _paso_como_dict(paso: Paso) -> dict[str, Any]:
    entidad = paso.entidad
    return {
        "orden": paso.orden,
        "verbo": paso.verbo,
        "entidad": {
            "tipo": entidad.tipo,
            "valor": entidad.valor,
            "normalizado": entidad.normalizado,
        }
        if entidad is not None
        else None,
        "tool": paso.tool,
        "parametros": paso.parametros,
        "estado": paso.estado,
        "motivo": paso.motivo,
        "texto": paso.texto,
    }