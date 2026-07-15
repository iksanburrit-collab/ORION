from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


_RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
_BASE_DATOS_PRUEBAS: Path | None = None


def raiz_proyecto() -> Path:
    return _BASE_DATOS_PRUEBAS or _RAIZ_PROYECTO


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
