from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SolicitudIA:
    mensaje: str
    contexto: str = ""
    historial: list[dict[str, str]] | None = None
    modelo: str = ""
    timeout: float = 30.0
    limite_salida: int = 180
    opciones: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RespuestaIA:
    texto: str
    proveedor: str
    modelo: str = ""
    error: bool = False
    tipo_error: str = ""
    latencia: float = 0.0
    codigo_estado: int | str | None = None
    diagnostico: dict[str, Any] = field(default_factory=dict)

