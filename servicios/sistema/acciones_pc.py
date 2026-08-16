from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
from typing import Any

from core.conocimiento import normalizar_para_busqueda
from servicios.sistema.aplicaciones import CatalogoAplicaciones
from servicios.sistema.contratos import ResultadoAccion


PROCESOS_CRITICOS = {
    "csrss.exe",
    "explorer.exe",
    "lsass.exe",
    "services.exe",
    "smss.exe",
    "system",
    "wininit.exe",
    "winlogon.exe",
    "init",
    "kernel_task",
    "launchd",
    "systemd",
}


def abrir_aplicacion(
    aplicacion: str,
    catalogo: CatalogoAplicaciones | None = None,
) -> ResultadoAccion:
    catalogo = catalogo or CatalogoAplicaciones()
    app = catalogo.buscar(aplicacion)

    if not app:
        return ResultadoAccion(
            False,
            "No encontre esa aplicacion. Quieres agregarla manualmente?",
            "abrir_aplicacion",
            tipo_error="aplicacion_no_registrada",
        )

    if not os.path.exists(app.ruta):
        return ResultadoAccion(
            False,
            "La ruta registrada ya no existe.",
            "abrir_aplicacion",
            tipo_error="ruta_inexistente",
        )

    comando, error_capacidad = _comando_apertura(app.ruta)
    if comando is None:
        return ResultadoAccion(
            False,
            error_capacidad or "No hay un lanzador compatible disponible.",
            "abrir_aplicacion",
            tipo_error="capacidad_no_disponible",
        )

    try:
        subprocess.Popen(comando, shell=False)
    except OSError as exc:
        return ResultadoAccion(
            False,
            "No pude abrir la aplicacion.",
            "abrir_aplicacion",
            error=str(exc),
            tipo_error="error_sistema",
        )

    return ResultadoAccion(
        True,
        f"Abriendo {app.nombre}.",
        "abrir_aplicacion",
        {"aplicacion": app.nombre},
    )


def cerrar_aplicacion(
    aplicacion: str,
    catalogo: CatalogoAplicaciones | None = None,
    procesos: list[dict[str, Any]] | None = None,
) -> ResultadoAccion:
    catalogo = catalogo or CatalogoAplicaciones()
    app = catalogo.buscar(aplicacion)

    if not app:
        return ResultadoAccion(
            False,
            "No cierro aplicaciones que no esten registradas.",
            "cerrar_aplicacion",
            tipo_error="aplicacion_no_registrada",
        )

    nombre_proceso = _nombre_proceso(app.ruta)
    if nombre_proceso in PROCESOS_CRITICOS:
        return ResultadoAccion(
            False,
            "Esa aplicacion esta protegida por seguridad.",
            "cerrar_aplicacion",
            tipo_error="proceso_critico",
        )

    if procesos is None:
        procesos, error_capacidad = _listar_procesos()
        if error_capacidad:
            return ResultadoAccion(
                False,
                error_capacidad,
                "cerrar_aplicacion",
                tipo_error="capacidad_no_disponible",
            )
    candidatos = [
        proceso
        for proceso in procesos
        if normalizar_para_busqueda(_nombre_proceso(str(proceso.get("name", ""))))
        == normalizar_para_busqueda(nombre_proceso)
    ]

    if not candidatos:
        return ResultadoAccion(
            False,
            "No encontre un proceso abierto para esa aplicacion.",
            "cerrar_aplicacion",
            tipo_error="proceso_no_encontrado",
        )

    cerrados = 0
    for proceso in candidatos:
        pid = str(proceso.get("pid", "")).strip()
        if pid.isdigit() and _terminar_proceso(pid):
            cerrados += 1

    if not cerrados:
        return ResultadoAccion(
            False,
            "No pude cerrar el proceso de esa aplicacion.",
            "cerrar_aplicacion",
            tipo_error="error_sistema",
        )

    return ResultadoAccion(
        True,
        f"Cerrando {app.nombre}.",
        "cerrar_aplicacion",
        {"aplicacion": app.nombre, "procesos": cerrados},
    )


def _comando_apertura(ruta: str) -> tuple[list[str] | None, str | None]:
    sistema = platform.system()
    extension = Path(ruta).suffix.lower()

    if sistema == "Darwin" and extension == ".app":
        return ["open", ruta], None

    if sistema == "Linux" and extension == ".desktop":
        lanzador = shutil.which("xdg-open")
        if not lanzador:
            return None, "No hay un lanzador de aplicaciones disponible (xdg-open)."
        return [lanzador, ruta], None

    if sistema in {"Windows", "Linux", "Darwin"}:
        return [ruta], None

    return None, f"Abrir aplicaciones no esta implementado para {sistema or 'este sistema'}."


def _nombre_proceso(ruta: str) -> str:
    nombre = os.path.basename(ruta).lower()
    if nombre.endswith(".app"):
        return Path(nombre).stem
    return nombre


def _listar_procesos() -> tuple[list[dict[str, Any]], str | None]:
    if platform.system() == "Windows":
        return _listar_procesos_windows(), None
    if platform.system() in {"Linux", "Darwin"}:
        return _listar_procesos_posix()
    return [], "Cerrar aplicaciones no esta implementado para este sistema."


def _listar_procesos_windows() -> list[dict[str, Any]]:
    try:
        resultado = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return []

    procesos = []
    for linea in resultado.stdout.splitlines():
        partes = [parte.strip('"') for parte in linea.split('","')]
        if len(partes) >= 2 and partes[1].isdigit():
            procesos.append({"name": partes[0], "pid": partes[1]})

    return procesos


def _listar_procesos_posix() -> tuple[list[dict[str, Any]], str | None]:
    try:
        resultado = subprocess.run(
            ["ps", "-axo", "pid=,comm="],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return [], "No pude listar los procesos del sistema."

    if resultado.returncode != 0:
        return [], "No pude listar los procesos del sistema."

    procesos = []
    for linea in resultado.stdout.splitlines():
        partes = linea.strip().split(maxsplit=1)
        if len(partes) == 2 and partes[0].isdigit():
            procesos.append({"pid": partes[0], "name": partes[1]})
    return procesos, None


def _terminar_proceso(pid: str) -> bool:
    try:
        if platform.system() == "Windows":
            resultado = subprocess.run(
                ["taskkill", "/PID", pid, "/T"],
                shell=False,
                check=False,
            )
            return resultado.returncode == 0

        if platform.system() in {"Linux", "Darwin"}:
            os.kill(int(pid), signal.SIGTERM)
            return True
    except (OSError, ValueError):
        return False

    return False
