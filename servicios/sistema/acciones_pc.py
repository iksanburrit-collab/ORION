from __future__ import annotations

import os
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

    try:
        subprocess.Popen([app.ruta], shell=False)
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

    nombre_proceso = os.path.basename(app.ruta).lower()
    if nombre_proceso in PROCESOS_CRITICOS:
        return ResultadoAccion(
            False,
            "Esa aplicacion esta protegida por seguridad.",
            "cerrar_aplicacion",
            tipo_error="proceso_critico",
        )

    procesos = procesos if procesos is not None else _listar_procesos_windows()
    candidatos = [
        proceso
        for proceso in procesos
        if normalizar_para_busqueda(str(proceso.get("name", "")))
        == normalizar_para_busqueda(nombre_proceso)
    ]

    if not candidatos:
        return ResultadoAccion(
            False,
            "No encontre un proceso abierto para esa aplicacion.",
            "cerrar_aplicacion",
            tipo_error="proceso_no_encontrado",
        )

    for proceso in candidatos:
        pid = str(proceso.get("pid", "")).strip()
        if not pid.isdigit():
            continue
        subprocess.run(["taskkill", "/PID", pid, "/T"], shell=False, check=False)

    return ResultadoAccion(
        True,
        f"Cerrando {app.nombre}.",
        "cerrar_aplicacion",
        {"aplicacion": app.nombre, "procesos": len(candidatos)},
    )


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
