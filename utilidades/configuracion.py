from __future__ import annotations

import copy
import os
from typing import Any

from ia.proveedor import (
    config_ia_migrada_correctamente,
    migrar_config_ia,
    requiere_migracion_config_ia,
)
from utilidades.archivos import cargar, guardar_json


CONFIG_PREDETERMINADA: dict[str, Any] = {
    "modo": "normal",
    "ia": {
        "activada": True,
        "router": {
            "orden_proveedores": [
                "groq",
                "ollama",
            ],
        },
        "proveedores": {
            "groq": {
                "activado": True,
                "modelo": "llama-3.1-8b-instant",
                "timeout": 15,
                "max_tokens": 180,
                "temperature": 0.6,
                "top_p": 0.9,
            },
            "ollama": {
                "activado": True,
                "modelo": "qwen3:1.7b",
                "timeout": 45,
                "keep_alive": "10m",
                "num_predict": 90,
                "num_ctx": 2048,
            },
            "futuro": {
                "activado": False,
                "tipo": "",
                "modelo": "",
            },
        },
        "limite_contexto": 700,
        "max_turnos": 4,
        "debug_rendimiento": False,
    },
}


def cargar_configuracion(
    nombre: str,
    defecto: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if defecto is None:
        defecto = CONFIG_PREDETERMINADA

    existe = os.path.exists(nombre)
    config = cargar(nombre, copy.deepcopy(defecto))

    if not isinstance(config, dict):
        config = copy.deepcopy(defecto)

    cambio = _completar_defaults_superiores(config, defecto)
    requiere_migracion = requiere_migracion_config_ia(config)

    if requiere_migracion:
        cambio = migrar_config_ia(config) or cambio

    if not config_ia_migrada_correctamente(config):
        return config

    if cambio or not existe:
        guardar_json(nombre, config)

    return config


def _completar_defaults_superiores(
    config: dict[str, Any],
    defecto: dict[str, Any],
) -> bool:
    cambio = False

    for clave, valor in defecto.items():
        if clave == "ia":
            continue

        if clave not in config:
            config[clave] = copy.deepcopy(valor)
            cambio = True

    return cambio
