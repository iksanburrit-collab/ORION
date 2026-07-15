from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoCargaJSON:
    datos: Any
    existe: bool
    error: str | None = None

    @property
    def correcto(self) -> bool:
        return self.error is None


def cargar_json(nombre: str, defecto: Any) -> ResultadoCargaJSON:
    ruta = Path(nombre)
    if not ruta.exists():
        return ResultadoCargaJSON(deepcopy(defecto), existe=False)

    try:
        with ruta.open("r", encoding="utf-8-sig") as archivo:
            return ResultadoCargaJSON(json.load(archivo), existe=True)
    except (json.JSONDecodeError, OSError, UnicodeError) as error:
        mensaje = f"No se pudo cargar JSON de {ruta}: {error}"
        LOGGER.warning(mensaje)
        return ResultadoCargaJSON(deepcopy(defecto), existe=True, error=mensaje)


def cargar(nombre: str, defecto: Any) -> Any:
    return cargar_json(nombre, defecto).datos


def guardar_json(nombre: str, datos: Any) -> None:
    ruta = Path(nombre)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = None

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(ruta.parent),
            prefix=f".{ruta.name}.",
            suffix=".tmp",
        ) as archivo:
            temporal = archivo.name
            json.dump(datos, archivo, indent=4, ensure_ascii=False)
            archivo.flush()
            os.fsync(archivo.fileno())

        os.replace(temporal, ruta)
    finally:
        if temporal and os.path.exists(temporal):
            os.unlink(temporal)


def asegurar_json(nombre: str, defecto: Any) -> Any:
    resultado = cargar_json(nombre, defecto)
    datos = resultado.datos

    if resultado.error:
        return datos

    cambio = _completar_defaults(datos, defecto)

    if not resultado.existe or cambio:
        guardar_json(nombre, datos)

    return datos


def _completar_defaults(datos: Any, defecto: Any) -> bool:
    if not isinstance(datos, dict) or not isinstance(defecto, dict):
        return False

    cambio = False

    for clave, valor in defecto.items():
        if clave not in datos:
            datos[clave] = deepcopy(valor)
            cambio = True
        elif isinstance(datos[clave], dict) and isinstance(valor, dict):
            cambio = _completar_defaults(datos[clave], valor) or cambio

    return cambio
