"""Carga mínima de variables desde .env sin dependencias externas."""

import os
from pathlib import Path


def cargar_entorno(ruta: str | Path = ".env") -> None:
    """Carga pares KEY=VALUE y conserva las variables ya definidas en el entorno."""
    archivo = Path(ruta)
    if not archivo.is_file():
        return

    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("export "):
            linea = linea.removeprefix("export ").strip()
        if "=" not in linea:
            continue

        clave, valor = linea.split("=", 1)
        clave = clave.strip()
        valor = valor.strip().strip("\"'")
        if clave:
            os.environ.setdefault(clave, valor)
