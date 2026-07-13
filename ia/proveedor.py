from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from core.memoria import construir_contexto_para_ia
from ia.nvidia import ERROR_NVIDIA, generar_respuesta_nvidia
from ia.ollama import ERROR_OLLAMA, generar_respuesta as generar_respuesta_ollama


@dataclass(frozen=True)
class RespuestaProveedor:
    texto: str
    proveedor: str
    error: bool = False
    metricas: dict[str, Any] = field(default_factory=dict)


def generar_respuesta(
    mensaje: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    historial: list[dict[str, str]] | None = None,
) -> RespuestaProveedor:
    config_ia = normalizar_config_ia(config)

    if not config_ia["activada"]:
        return RespuestaProveedor("", "desactivada", error=True)

    inicio_contexto = time.perf_counter()
    contexto = construir_contexto_para_ia(
        memoria,
        consulta=mensaje,
        limite=config_ia["limite_contexto"],
    )
    tiempo_contexto = time.perf_counter() - inicio_contexto
    proveedor = config_ia["proveedor"]

    if proveedor == "ollama":
        return _responder_ollama(mensaje, contexto, historial, config_ia, tiempo_contexto)

    if proveedor == "nvidia":
        respuesta = _responder_nvidia(
            mensaje,
            contexto,
            historial,
            config_ia,
            tiempo_contexto,
        )

        if not respuesta.error:
            return respuesta

        if config_ia["fallback_local"]:
            fallback = _responder_ollama(
                mensaje,
                contexto,
                historial,
                config_ia,
                tiempo_contexto,
            )

            if not fallback.error:
                return fallback

            return RespuestaProveedor(
                _mensaje_error_final(respuesta.texto, fallback.texto),
                "ninguno",
                error=True,
                metricas=fallback.metricas,
            )

        return respuesta

    return RespuestaProveedor(
        "No pude usar IA: proveedor no reconocido.",
        "ninguno",
        error=True,
    )


def normalizar_config_ia(config: dict[str, Any]) -> dict[str, Any]:
    ia = config.get("ia", {})

    if not isinstance(ia, dict):
        ia = {}

    nvidia = ia.get("nvidia", {})
    ollama = ia.get("ollama", {})

    if not isinstance(nvidia, dict):
        nvidia = {}

    if not isinstance(ollama, dict):
        ollama = {}

    return {
        "activada": bool(ia.get("activada", True)),
        "proveedor": str(ia.get("proveedor", "nvidia") or "nvidia").lower(),
        "fallback_local": bool(ia.get("fallback_local", True)),
        "limite_contexto": int(_numero_config(
            ia.get("limite_contexto"),
            900.0,
        )),
        "max_turnos": int(_numero_config(
            ia.get("max_turnos", ia.get("max_turnos_conversacion")),
            4.0,
        )),
        "debug_rendimiento": bool(ia.get("debug_rendimiento", False)),
        "nvidia": {
            "modelo": str(
                nvidia.get(
                    "modelo",
                    "meta/llama-4-maverick-17b-128e-instruct",
                )
            ),
            "timeout": _numero_config(nvidia.get("timeout"), 25.0),
            "max_tokens": int(_numero_config(nvidia.get("max_tokens"), 180.0)),
        },
        "ollama": {
            "modelo": str(ollama.get("modelo", ia.get("modelo", "qwen3:1.7b"))),
            "timeout": _numero_config(
                ollama.get("timeout", ia.get("timeout")),
                60.0,
            ),
            "keep_alive": str(
                ollama.get("keep_alive", ia.get("keep_alive", "10m")) or "10m"
            ),
            "num_predict": int(_numero_config(
                ollama.get("num_predict", ia.get("num_predict")),
                100.0,
            )),
            "num_ctx": int(_numero_config(
                ollama.get("num_ctx", ia.get("num_ctx")),
                2048.0,
            )),
        },
    }


def _responder_nvidia(
    mensaje: str,
    contexto: str,
    historial: list[dict[str, str]] | None,
    config_ia: dict[str, Any],
    tiempo_contexto: float,
) -> RespuestaProveedor:
    inicio = time.perf_counter()
    respuesta = generar_respuesta_nvidia(
        mensaje,
        contexto=contexto,
        historial=historial,
        modelo=config_ia["nvidia"]["modelo"],
        timeout=config_ia["nvidia"]["timeout"],
        max_tokens=config_ia["nvidia"]["max_tokens"],
    )
    tiempo_respuesta = time.perf_counter() - inicio
    error = respuesta.startswith(ERROR_NVIDIA)

    return RespuestaProveedor(
        respuesta,
        "nvidia",
        error=error,
        metricas=_metricas(
            "nvidia",
            contexto,
            respuesta,
            tiempo_contexto,
            tiempo_respuesta,
            config_ia,
        ),
    )


def _responder_ollama(
    mensaje: str,
    contexto: str,
    historial: list[dict[str, str]] | None,
    config_ia: dict[str, Any],
    tiempo_contexto: float,
) -> RespuestaProveedor:
    inicio = time.perf_counter()
    respuesta = generar_respuesta_ollama(
        mensaje,
        contexto=contexto,
        historial=historial,
        modelo=config_ia["ollama"]["modelo"],
        timeout=config_ia["ollama"]["timeout"],
        keep_alive=config_ia["ollama"]["keep_alive"],
        limite_respuesta=config_ia["ollama"]["num_predict"] * 8,
        num_predict=config_ia["ollama"]["num_predict"],
        num_ctx=config_ia["ollama"]["num_ctx"],
    )
    tiempo_respuesta = time.perf_counter() - inicio
    error = respuesta.startswith(ERROR_OLLAMA)

    return RespuestaProveedor(
        respuesta,
        "ollama",
        error=error,
        metricas=_metricas(
            "ollama",
            contexto,
            respuesta,
            tiempo_contexto,
            tiempo_respuesta,
            config_ia,
        ),
    )


def _metricas(
    proveedor: str,
    contexto: str,
    respuesta: str,
    tiempo_contexto: float,
    tiempo_respuesta: float,
    config_ia: dict[str, Any],
) -> dict[str, Any]:
    if not config_ia.get("debug_rendimiento"):
        return {}

    return {
        "proveedor": proveedor,
        "tiempo_contexto": round(tiempo_contexto, 4),
        "tiempo_respuesta": round(tiempo_respuesta, 4),
        "longitud_contexto": len(contexto),
        "longitud_respuesta": len(respuesta),
    }


def _mensaje_error_final(error_principal: str, error_fallback: str) -> str:
    if error_fallback:
        return error_fallback

    return error_principal or "No pude usar IA en este momento."


def _numero_config(valor: Any, defecto: float) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return defecto

    return numero if numero > 0 else defecto
