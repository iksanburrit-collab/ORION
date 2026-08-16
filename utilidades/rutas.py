from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import platform
from typing import Iterator

from platformdirs import user_data_dir


_RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
_BASE_DATOS_PRUEBAS: Path | None = None
_ARCHIVOS_LEGACY = (
    "memoria.json",
    "notas.json",
    "recordatorios.json",
    "config.json",
    "alias.json",
)

# Preserva las ubicaciones históricas por plataforma: en Linux el directorio
# se creó en minúsculas ("orion") y en el resto de sistemas en mayúsculas.
_NOMBRE_APP_LINUX = "orion"
_NOMBRE_APP = "ORION"


def _directorio_plataforma() -> Path:
    nombre = _NOMBRE_APP_LINUX if platform.system() == "Linux" else _NOMBRE_APP
    return Path(user_data_dir(nombre, appauthor=False))


def raiz_proyecto() -> Path:
    if _BASE_DATOS_PRUEBAS is not None:
        return _BASE_DATOS_PRUEBAS

    ruta_configurada = os.environ.get("ORION_DATA_DIR")
    if ruta_configurada:
        return Path(ruta_configurada).expanduser().resolve()

    # Mantiene los datos de instalaciones previas que se guardaban junto al código.
    if any((_RAIZ_PROYECTO / archivo).exists() for archivo in _ARCHIVOS_LEGACY):
        return _RAIZ_PROYECTO

    return _directorio_plataforma()


def configurar_base_datos(ruta: str | Path | None) -> None:
    global _BASE_DATOS_PRUEBAS
    _BASE_DATOS_PRUEBAS = Path(ruta).resolve() if ruta is not None else None


@contextmanager
def usar_base_datos(ruta: str | Path) -> Iterator[Path]:
    anterior = _BASE_DATOS_PRUEBAS
    configurar_base_datos(ruta)
    try:
        yield raiz_proyecto()
    finally:
        configurar_base_datos(anterior)


def ruta_memoria() -> str:
    return str(raiz_proyecto() / "memoria.json")


def ruta_notas() -> str:
    return str(raiz_proyecto() / "notas.json")


def ruta_recordatorios() -> str:
    return str(raiz_proyecto() / "recordatorios.json")


def ruta_configuracion() -> str:
    return str(raiz_proyecto() / "config.json")


def ruta_alias() -> str:
    return str(raiz_proyecto() / "alias.json")


def ruta_calendario_local() -> str:
    return str(raiz_proyecto() / "datos" / "calendario_local.json")


def ruta_aplicaciones_usuario() -> str:
    return str(raiz_proyecto() / "datos" / "aplicaciones_usuario.json")
