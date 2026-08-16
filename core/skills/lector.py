from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.skills.contratos import Skill


_NOMBRE_SKILL = re.compile(r"[a-z0-9_\-]+")

_SECCIONES = {
    "cuando_utilizar": "cuándo utilizar",
    "herramientas_relacionadas": "herramientas relacionadas",
    "reglas": "reglas",
}


def leer_skill(ruta_dir: str | Path) -> Skill | None:
    """Lee SKILL.md de un directorio y lo convierte en Skill.

    Devuelve None si el directorio no contiene una Skill valida (falta el
    archivo, el nombre no es valido o no hay descripcion).
    """
    directorio = Path(ruta_dir)
    archivo = directorio / "SKILL.md"
    if not archivo.is_file():
        return None

    try:
        texto = archivo.read_text(encoding="utf-8")
    except OSError:
        return None

    frontal, cuerpo = _separar_frontal(texto)
    nombre = str(frontal.get("nombre") or directorio.name).strip()
    descripcion = str(frontal.get("descripcion") or "").strip()

    if not _NOMBRE_SKILL.fullmatch(nombre) or not descripcion:
        return None

    metadata = _parsear_secciones(cuerpo)
    metadata["fuente"] = str(archivo)

    return Skill(
        name=nombre,
        description=descripcion,
        instructions=cuerpo.strip(),
        metadata=metadata,
    )


def _separar_frontal(texto: str) -> tuple[dict[str, str], str]:
    if not texto.startswith("---"):
        return {}, texto

    lineas = texto.splitlines()
    if len(lineas) < 2:
        return {}, texto

    fin = None
    for indice in range(1, len(lineas)):
        if lineas[indice].strip() == "---":
            fin = indice
            break

    if fin is None:
        return {}, texto

    frontal: dict[str, str] = {}
    for linea in lineas[1:fin]:
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            frontal[clave.strip()] = valor.strip()

    return frontal, "\n".join(lineas[fin + 1:])


def _parsear_secciones(cuerpo: str) -> dict[str, Any]:
    secciones: dict[str, Any] = {}
    titulo_actual: str | None = None

    for linea in cuerpo.splitlines():
        linea_normalizada = linea.strip().lower()

        if linea_normalizada.startswith("## "):
            titulo_actual = None
            for clave, titulo in _SECCIONES.items():
                if linea_normalizada == f"## {titulo}":
                    titulo_actual = clave
                    secciones[clave] = []
                    break
            continue

        if titulo_actual is not None and linea_normalizada.startswith("- "):
            secciones[titulo_actual].append(linea_normalizada[2:].strip())

    return {clave: valor for clave, valor in secciones.items() if valor}