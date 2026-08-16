"""Carga mínima de variables desde .env sin dependencias externas."""

import os
from pathlib import Path

from utilidades.rutas import raiz_proyecto


def _ruta_env() -> Path:
    raiz = raiz_proyecto()
    candidatas = [
        raiz / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(".env").resolve(),
    ]
    for candidata in candidatas:
        if candidata.is_file():
            return candidata
    return candidatas[0]


def cargar_entorno(ruta: str | Path | None = None) -> None:
    """Carga pares KEY=VALUE y conserva las variables ya definidas en el entorno.

    Si no se indica ruta, busca .env en el directorio de datos de ORION
    (ORION_DATA_DIR o el directorio de datos de la plataforma) y, como
    respaldo, junto al proyecto o en el directorio actual.
    """
    archivo = Path(ruta) if ruta is not None else _ruta_env()
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
