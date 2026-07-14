from __future__ import annotations

import copy
import time
from typing import Any, Callable

from core.memoria import construir_contexto_para_ia
from ia.contratos import RespuestaIA, SolicitudIA
from ia import groq, ollama


AdaptadorProveedor = Callable[[SolicitudIA], RespuestaIA]

PROVEEDORES: dict[str, AdaptadorProveedor] = {
    "groq": groq.responder,
    "ollama": ollama.responder,
}

RespuestaProveedor = RespuestaIA

_CLAVES_LEGACY_IA = {
    "proveedor",
    "fallback_local",
    "modelo",
    "timeout",
    "keep_alive",
    "num_predict",
    "num_ctx",
    "max_turnos_conversacion",
    "nvidia",
    "ollama",
}


def generar_respuesta(
    mensaje: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    historial: list[dict[str, str]] | None = None,
) -> RespuestaIA:
    config_ia = normalizar_config_ia(config)

    if not config_ia["activada"]:
        return RespuestaIA("", "desactivada", error=True, tipo_error="ia_desactivada")

    inicio_contexto = time.perf_counter()
    contexto = construir_contexto_para_ia(
        memoria,
        consulta=mensaje,
        limite=config_ia["limite_contexto"],
    )
    tiempo_contexto = round(time.perf_counter() - inicio_contexto, 4)
    errores: list[RespuestaIA] = []
    proveedores_probados: list[str] = []

    for nombre in config_ia["router"]["orden_proveedores"]:
        if nombre in proveedores_probados:
            continue

        proveedores_probados.append(nombre)
        adaptador = PROVEEDORES.get(nombre)
        config_proveedor = config_ia["proveedores"].get(nombre, {})

        if adaptador is None or not config_proveedor.get("activado", False):
            continue

        solicitud = _crear_solicitud(
            mensaje,
            contexto,
            historial,
            config_proveedor,
        )
        respuesta = adaptador(solicitud)
        metricas = _metricas(
            respuesta,
            contexto,
            tiempo_contexto,
            errores,
            fallback=bool(errores),
            intentos=proveedores_probados,
            debug=config_ia["debug_rendimiento"],
        )

        if not respuesta.error:
            return _con_metricas(respuesta, metricas)

        errores.append(respuesta)

    return RespuestaIA(
        texto=_mensaje_error_final(errores),
        proveedor="ninguno",
        error=True,
        tipo_error="todos_fallaron",
        diagnostico=_metricas_error_final(
            errores,
            proveedores_probados,
            tiempo_contexto,
            config_ia["debug_rendimiento"],
        ),
    )


def normalizar_config_ia(config: dict[str, Any]) -> dict[str, Any]:
    ia = config.get("ia", {})

    if not isinstance(ia, dict):
        ia = {}

    proveedores_config = ia.get("proveedores", {})

    if not isinstance(proveedores_config, dict):
        proveedores_config = {}

    proveedor_legacy = str(ia.get("proveedor", "") or "").lower()
    orden_legacy = _orden_desde_legacy(proveedor_legacy, ia.get("fallback_local", True))
    router = ia.get("router", {})

    if not isinstance(router, dict):
        router = {}

    orden = router.get("orden_proveedores", orden_legacy)
    groq_config = _config_dict(proveedores_config.get("groq"))
    ollama_config = _config_dict(proveedores_config.get("ollama", ia.get("ollama", {})))
    futuro_config = _config_dict(proveedores_config.get("futuro"))

    return {
        "activada": bool(ia.get("activada", True)),
        "router": {
            "orden_proveedores": _normalizar_orden(orden),
        },
        "proveedores": {
            "groq": {
                "activado": bool(groq_config.get("activado", True)),
                "modelo": str(groq_config.get("modelo", "llama-3.1-8b-instant") or ""),
                "timeout": _numero_config(groq_config.get("timeout"), 15.0),
                "max_tokens": int(_numero_config(groq_config.get("max_tokens"), 180.0)),
                "temperature": _numero_config(groq_config.get("temperature"), 0.6),
                "top_p": _numero_config(groq_config.get("top_p"), 0.9),
            },
            "ollama": {
                "activado": bool(ollama_config.get("activado", True)),
                "modelo": str(
                    ollama_config.get("modelo", ia.get("modelo", "qwen3:1.7b"))
                    or "qwen3:1.7b"
                ),
                "timeout": _numero_config(
                    ollama_config.get("timeout", ia.get("timeout")),
                    45.0,
                ),
                "keep_alive": str(
                    ollama_config.get("keep_alive", ia.get("keep_alive", "10m"))
                    or "10m"
                ),
                "num_predict": int(_numero_config(
                    ollama_config.get("num_predict", ia.get("num_predict")),
                    90.0,
                )),
                "num_ctx": int(_numero_config(
                    ollama_config.get("num_ctx", ia.get("num_ctx")),
                    2048.0,
                )),
            },
            "futuro": {
                "activado": bool(futuro_config.get("activado", False)),
                "tipo": str(futuro_config.get("tipo", "") or ""),
                "modelo": str(futuro_config.get("modelo", "") or ""),
            },
        },
        "limite_contexto": int(_numero_config(ia.get("limite_contexto"), 700.0)),
        "max_turnos": int(_numero_config(
            ia.get("max_turnos", ia.get("max_turnos_conversacion")),
            4.0,
        )),
        "debug_rendimiento": bool(ia.get("debug_rendimiento", False)),
    }


def migrar_config_ia(config: dict[str, Any]) -> bool:
    ia_original = config.get("ia")

    if not isinstance(ia_original, dict):
        migrada = normalizar_config_ia(config)
        candidato = dict(config)
        candidato["ia"] = migrada

        if not config_ia_migrada_correctamente(candidato):
            return False

        config["ia"] = migrada
        return True

    if not requiere_migracion_config_ia(config):
        return False

    migrada = normalizar_config_ia(config)
    cambio = ia_original != migrada

    candidato = dict(config)
    candidato["ia"] = migrada

    if not config_ia_migrada_correctamente(candidato):
        return False

    config["ia"] = migrada
    return cambio


def requiere_migracion_config_ia(config: dict[str, Any]) -> bool:
    ia = config.get("ia")

    if not isinstance(ia, dict):
        return True

    if any(clave in ia for clave in _CLAVES_LEGACY_IA):
        return True

    proveedores = ia.get("proveedores")
    router = ia.get("router")

    if not isinstance(router, dict):
        return True

    if not isinstance(router.get("orden_proveedores"), list):
        return True

    if not isinstance(proveedores, dict):
        return True

    if (
        "groq" not in proveedores
        or "ollama" not in proveedores
        or "futuro" not in proveedores
    ):
        return True

    return False


def config_ia_migrada_correctamente(config: dict[str, Any]) -> bool:
    ia = config.get("ia")

    if not isinstance(ia, dict):
        return False

    if any(clave in ia for clave in _CLAVES_LEGACY_IA):
        return False

    router = ia.get("router")
    proveedores = ia.get("proveedores")

    if not isinstance(router, dict) or not isinstance(proveedores, dict):
        return False

    orden = router.get("orden_proveedores")

    if not isinstance(orden, list) or not orden:
        return False

    for nombre in ("groq", "ollama", "futuro"):
        if not isinstance(proveedores.get(nombre), dict):
            return False

    return "groq" in orden or "ollama" in orden


def _crear_solicitud(
    mensaje: str,
    contexto: str,
    historial: list[dict[str, str]] | None,
    config_proveedor: dict[str, Any],
) -> SolicitudIA:
    opciones = copy.deepcopy(config_proveedor)
    modelo = str(opciones.pop("modelo", "") or "")
    timeout = _numero_config(opciones.pop("timeout", 30.0), 30.0)
    limite_salida = int(_numero_config(
        opciones.pop("max_tokens", opciones.get("num_predict")),
        180.0,
    ))
    opciones.pop("activado", None)

    return SolicitudIA(
        mensaje=mensaje,
        contexto=contexto,
        historial=historial,
        modelo=modelo,
        timeout=timeout,
        limite_salida=limite_salida,
        opciones=opciones,
    )


def _metricas(
    respuesta: RespuestaIA,
    contexto: str,
    tiempo_contexto: float,
    errores_previos: list[RespuestaIA],
    fallback: bool,
    intentos: list[str],
    debug: bool,
) -> dict[str, Any]:
    if not debug:
        return {}

    return {
        "proveedor": respuesta.proveedor,
        "modelo": respuesta.modelo,
        "latencia": respuesta.latencia,
        "tiempo_contexto": tiempo_contexto,
        "longitud_contexto": len(contexto),
        "longitud_respuesta": len(respuesta.texto),
        "tipo_error": respuesta.tipo_error,
        "codigo_estado": respuesta.codigo_estado,
        "fallback": fallback,
        "intentos": list(intentos),
        "errores_previos": [
            _resumen_error(error_previo)
            for error_previo in errores_previos
        ],
    }


def _metricas_error_final(
    errores: list[RespuestaIA],
    intentos: list[str],
    tiempo_contexto: float,
    debug: bool,
) -> dict[str, Any]:
    if not debug:
        return {}

    return {
        "proveedor": "ninguno",
        "tiempo_contexto": tiempo_contexto,
        "fallback": len(errores) > 1,
        "intentos": list(intentos),
        "errores": [_resumen_error(error) for error in errores],
    }


def _resumen_error(respuesta: RespuestaIA) -> dict[str, Any]:
    return {
        "proveedor": respuesta.proveedor,
        "modelo": respuesta.modelo,
        "tipo_error": respuesta.tipo_error,
        "latencia": respuesta.latencia,
        "codigo_estado": respuesta.codigo_estado,
    }


def _con_metricas(respuesta: RespuestaIA, metricas: dict[str, Any]) -> RespuestaIA:
    if not metricas:
        return respuesta

    diagnostico = dict(respuesta.diagnostico)
    diagnostico.update(metricas)

    return RespuestaIA(
        texto=respuesta.texto,
        proveedor=respuesta.proveedor,
        modelo=respuesta.modelo,
        error=respuesta.error,
        tipo_error=respuesta.tipo_error,
        latencia=respuesta.latencia,
        codigo_estado=respuesta.codigo_estado,
        diagnostico=diagnostico,
    )


def _mensaje_error_final(errores: list[RespuestaIA]) -> str:
    if not errores:
        return "No hay proveedores de IA disponibles."

    return errores[-1].texto or "No pude usar IA en este momento."


def _orden_desde_legacy(proveedor: str, fallback_local: Any) -> list[str]:
    if proveedor == "ollama":
        return ["ollama"]

    if proveedor == "groq":
        return ["groq", "ollama"] if bool(fallback_local) else ["groq"]

    return ["groq", "ollama"]


def _normalizar_orden(orden: Any) -> list[str]:
    if not isinstance(orden, list):
        orden = ["groq", "ollama"]

    resultado: list[str] = []

    for proveedor in orden:
        nombre = str(proveedor or "").lower()

        if nombre and nombre not in resultado:
            resultado.append(nombre)

    return resultado or ["groq", "ollama"]


def _config_dict(valor: Any) -> dict[str, Any]:
    return valor if isinstance(valor, dict) else {}


def _numero_config(valor: Any, defecto: float) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return defecto

    return numero if numero > 0 else defecto
