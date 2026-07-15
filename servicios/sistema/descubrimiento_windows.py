from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from servicios.sistema.aplicaciones import ruta_permitida
from servicios.sistema.contratos import AplicacionRegistrada


def descubrir_aplicaciones_windows() -> list[AplicacionRegistrada]:
    detectadas: list[AplicacionRegistrada] = []

    for carpeta in _carpetas_inicio():
        detectadas.extend(_leer_accesos_directos(carpeta))

    detectadas.extend(_leer_rutas_comunes())
    return _deduplicar(detectadas)


def _carpetas_inicio() -> list[Path]:
    rutas = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")

    if appdata:
        rutas.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

    if programdata:
        rutas.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

    return rutas


def _leer_accesos_directos(carpeta: Path) -> list[AplicacionRegistrada]:
    if not carpeta.exists():
        return []

    apps = []
    for ruta in carpeta.rglob("*.lnk"):
        if ruta_permitida(str(ruta)):
            apps.append(_crear_app(ruta, "menu_inicio"))

    return apps


def _leer_rutas_comunes() -> list[AplicacionRegistrada]:
    candidatos = []
    nombres = {
        "Visual Studio Code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
        ],
        "Bloc de notas": [
            os.path.expandvars(r"%WINDIR%\System32\notepad.exe"),
        ],
    }

    for nombre, rutas in nombres.items():
        for ruta in rutas:
            if os.path.exists(ruta) and ruta_permitida(ruta):
                candidatos.append(
                    AplicacionRegistrada(
                        nombre=nombre,
                        aliases=_aliases(nombre),
                        ruta=ruta,
                        origen="ruta_comun",
                        verificada=True,
                        ultima_deteccion=_fecha_iso(),
                    )
                )

    return candidatos


def _crear_app(ruta: Path, origen: str) -> AplicacionRegistrada:
    nombre = ruta.stem
    return AplicacionRegistrada(
        nombre=nombre,
        aliases=_aliases(nombre),
        ruta=str(ruta),
        origen=origen,
        verificada=True,
        ultima_deteccion=_fecha_iso(),
    )


def _aliases(nombre: str) -> list[str]:
    base = nombre.lower().replace(" ", "")
    aliases = [base]

    if "visual studio code" in nombre.lower():
        aliases.extend(["vscode", "code"])
    if "bloc" in nombre.lower() or "notepad" in nombre.lower():
        aliases.extend(["notepad", "bloc de notas"])

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
