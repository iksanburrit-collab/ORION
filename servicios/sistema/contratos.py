from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AplicacionRegistrada:
    nombre: str
    aliases: list[str]
    ruta: str
    tipo: str = "aplicacion"
    origen: str = "manual"
    verificada: bool = False
    ultima_deteccion: str = ""

    def como_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "aliases": self.aliases,
            "ruta": self.ruta,
            "tipo": self.tipo,
            "origen": self.origen,
            "verificada": self.verificada,
            "ultima_deteccion": self.ultima_deteccion,
        }

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> "AplicacionRegistrada":
        aliases = datos.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = []

        return cls(
            nombre=str(datos.get("nombre", "")).strip(),
            aliases=[str(alias).strip() for alias in aliases if str(alias).strip()],
            ruta=str(datos.get("ruta", "")).strip(),
            tipo=str(datos.get("tipo", "aplicacion")),
            origen=str(datos.get("origen", "manual")),
            verificada=bool(datos.get("verificada", False)),
            ultima_deteccion=str(datos.get("ultima_deteccion", "")),
        )


@dataclass
class AccionPC:
    nombre: str
    descripcion: str
    parametros_permitidos: list[str]
    nivel_riesgo: str
    requiere_confirmacion: bool
    sistemas_compatibles: list[str]
    ejecutor: Callable[..., "ResultadoAccion"]


@dataclass
class ResultadoAccion:
    exito: bool
    mensaje: str
    accion: str
    detalles_seguros: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    tipo_error: str = ""
