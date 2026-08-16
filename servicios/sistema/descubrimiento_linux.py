from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from servicios.sistema.aplicaciones import ruta_permitida
from servicios.sistema.contratos import AplicacionRegistrada


def descubrir_aplicaciones_linux(
    carpetas: list[Path] | None = None,
) -> list[AplicacionRegistrada]:
    """Descubre aplicaciones Linux a partir de archivos .desktop en las rutas XDG."""
    carpetas = carpetas if carpetas is not None else _carpetas_aplicaciones()

    detectadas: list[AplicacionRegistrada] = []
    for carpeta in carpetas:
        detectadas.extend(_leer_carpeta(carpeta))

    return _deduplicar(detectadas)


def _carpetas_aplicaciones() -> list[Path]:
    rutas: list[Path] = []

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        rutas.append(Path(xdg_data_home) / "applications")

    rutas.append(Path.home() / ".local" / "share" / "applications")

    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    for directorio in xdg_data_dirs.split(":"):
        if directorio:
            rutas.append(Path(directorio) / "applications")

    return rutas


def _leer_carpeta(carpeta: Path) -> list[AplicacionRegistrada]:
    if not carpeta.exists():
        return []

    apps = []
    for ruta in carpeta.rglob("*.desktop"):
        if not ruta.is_file():
            continue

        app = _leer_desktop(ruta)
        if app is not None:
            apps.append(app)

    return apps


def _leer_desktop(ruta: Path) -> AplicacionRegistrada | None:
    if not ruta_permitida(str(ruta)):
        return None

    try:
        lineas = ruta.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None

    nombre: str | None = None
    oculta = False
    en_entrada = False

    for linea in lineas:
        linea = linea.strip()

        if not en_entrada:
            if linea == "[Desktop Entry]":
                en_entrada = True
            continue

        if linea.startswith("["):
            break

        clave, valor = _clave_valor(linea)
        if clave == "Type" and valor and valor.lower() != "application":
            return None
        if clave in {"NoDisplay", "Hidden"} and _es_verdadero(valor):
            oculta = True
        if clave == "Name" and nombre is None:
            nombre = valor

    if not nombre or oculta:
        return None

    return AplicacionRegistrada(
        nombre=nombre,
        aliases=_aliases(nombre),
        ruta=str(ruta),
        origen="desktop",
        verificada=True,
        ultima_deteccion=_fecha_iso(),
    )


def _clave_valor(linea: str) -> tuple[str, str]:
    if "=" not in linea:
        return "", ""
    clave, valor = linea.split("=", 1)
    return clave.strip(), valor.strip()


def _es_verdadero(valor: str) -> bool:
    return valor.lower() in {"true", "1", "yes"}


def _aliases(nombre: str) -> list[str]:
    base = nombre.lower().replace(" ", "")
    aliases = [base]

    if "brave" in nombre.lower():
        aliases.append("brave")
    if "firefox" in nombre.lower():
        aliases.append("firefox")
    if "steam" in nombre.lower():
        aliases.append("steam")
    if "visual studio code" in nombre.lower():
        aliases.extend(["vscode", "code"])

    return sorted(set(aliases))


def _deduplicar(apps: list[AplicacionRegistrada]) -> list[AplicacionRegistrada]:
    vistas = set()
    resultado = []

    for app in apps:
        clave = (app.nombre.lower(), app.ruta.lower())
        if clave in vistas:
            continue

        vistas.add(clave)
        resultado.append(app)

    return resultado


def _fecha_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")