from __future__ import annotations

from servicios.sistema.contratos import AccionPC


RIESGO_BAJO = "bajo"
RIESGO_MEDIO = "medio"
RIESGO_ALTO = "alto"


def accion_permitida(accion: AccionPC, config: dict) -> tuple[bool, str]:
    sistema = config.get("sistema", {}) if isinstance(config, dict) else {}

    if not sistema.get("control_pc_activado", True):
        return False, "El control del PC esta desactivado."

    if accion.nivel_riesgo == RIESGO_ALTO and not sistema.get("permitir_riesgo_alto", False):
        return False, "Las acciones de riesgo alto estan desactivadas."

    return True, ""


def requiere_confirmacion(accion: AccionPC, config: dict) -> bool:
    sistema = config.get("sistema", {}) if isinstance(config, dict) else {}

    if accion.requiere_confirmacion:
        return True

    if accion.nivel_riesgo == RIESGO_MEDIO:
        return sistema.get("confirmar_riesgo_medio", True)

    return accion.nivel_riesgo == RIESGO_ALTO
