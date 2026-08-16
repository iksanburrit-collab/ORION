from __future__ import annotations

from typing import Any

from core.handlers.contratos import ResultadoCerebro
from core.memoria import (
    guardar_memoria,
    obtener_historial_conversacion,
    registrar_turno_conversacion,
)
from ia.proveedor import generar_respuesta, normalizar_config_ia


def resolver_ia(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    resultado: ResultadoCerebro,
) -> bool:
    config_ia = normalizar_config_ia(config)

    if not config_ia["activada"]:
        return False

    historial = obtener_historial_conversacion(
        memoria,
        limite=config_ia["max_turnos"],
    )
    respuesta = generar_respuesta(
        texto,
        memoria,
        config,
        historial=historial,
    )

    resultado.respuesta = respuesta.texto
    resultado.debug = respuesta.diagnostico or None

    if respuesta.error:
        resultado.accion = "error_ia"
    else:
        resultado.accion = f"respuesta_ia_{respuesta.proveedor}"

    if not respuesta.error:
        registrar_turno_conversacion(
            memoria,
            texto,
            respuesta.texto,
            limite=config_ia["max_turnos"],
        )
        guardar_memoria(memoria)

    return True