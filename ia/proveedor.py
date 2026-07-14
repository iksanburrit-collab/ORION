from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from core.memoria import construir_contexto_para_ia
from ia.nvidia import (
    ERROR_NVIDIA,
    DiagnosticoNvidia,
    generar_respuesta_nvidia_diagnostico,
)
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
            if config_ia["debug_rendimiento"]:
                _imprimir_debug_fallback()

            fallback = _responder_ollama(
                mensaje,
                contexto,
                historial,
                config_ia,
                tiempo_contexto,
            )

            if not fallback.error:
                return RespuestaProveedor(
                    fallback.texto,
                    fallback.proveedor,
                    error=False,
                    metricas=_combinar_metricas_fallback(
                        respuesta.metricas,
                        fallback.metricas,
                    ),
                )

            return RespuestaProveedor(
                _mensaje_error_final(respuesta.texto, fallback.texto),
                "ninguno",
                error=True,
                metricas=_combinar_metricas_fallback(
                    respuesta.metricas,
                    fallback.metricas,
                ),
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
    diagnostico = generar_respuesta_nvidia_diagnostico(
        mensaje,
        contexto=contexto,
        historial=historial,
        modelo=config_ia["nvidia"]["modelo"],
        timeout=config_ia["nvidia"]["timeout"],
        max_tokens=config_ia["nvidia"]["max_tokens"],
    )
    respuesta = diagnostico.texto
    tiempo_respuesta = diagnostico.tiempo
    error = respuesta.startswith(ERROR_NVIDIA)
    metricas = _metricas(
        "nvidia",
        contexto,
        respuesta,
        tiempo_contexto,
        tiempo_respuesta,
        config_ia,
        diagnostico=diagnostico,
    )

    return RespuestaProveedor(
        respuesta,
        "nvidia",
        error=error,
        metricas=metricas,
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
    diagnostico: DiagnosticoNvidia | None = None,
) -> dict[str, Any]:
    if not config_ia.get("debug_rendimiento"):
        return {}

    metricas = {
        "proveedor": proveedor,
        "tiempo_contexto": round(tiempo_contexto, 4),
        "tiempo_respuesta": round(tiempo_respuesta, 4),
        "longitud_contexto": len(contexto),
        "longitud_respuesta": len(respuesta),
    }

    if diagnostico is not None:
        metricas.update({
            "endpoint": diagnostico.endpoint,
            "modelo": diagnostico.modelo,
            "api_detectada": diagnostico.api_detectada,
            "http": diagnostico.http,
            "mensaje": diagnostico.mensaje,
            "timeout": diagnostico.timeout,
            "lineas_debug": _lineas_debug_nvidia(
                diagnostico,
                contexto,
                respuesta,
            ),
        })

        _imprimir_lineas_debug(metricas["lineas_debug"])

    return metricas


def _lineas_debug_nvidia(
    diagnostico: DiagnosticoNvidia,
    contexto: str,
    respuesta: str,
) -> list[str]:
    estado_respuesta = "OK"

    if respuesta.startswith(ERROR_NVIDIA):
        estado_respuesta = diagnostico.mensaje or "Error"

    return [
        "[IA DEBUG]",
        "Proveedor seleccionado:",
        "NVIDIA",
        "API KEY:",
        "Detectada" if diagnostico.api_detectada else "No detectada",
        "Contexto:",
        f"{len(contexto)} caracteres",
        "Tiempo NVIDIA:",
        f"{diagnostico.tiempo:.2f} s",
        "HTTP:",
        str(diagnostico.http if diagnostico.http is not None else "Sin respuesta"),
        "Respuesta:",
        estado_respuesta,
    ]


def _imprimir_debug_fallback() -> None:
    print("[IA DEBUG]")
    print("NVIDIA fallo, iniciando Ollama")


def _imprimir_lineas_debug(lineas: list[str]) -> None:
    for linea in lineas:
        print(linea)


def _combinar_metricas_fallback(
    metricas_nvidia: dict[str, Any],
    metricas_ollama: dict[str, Any],
) -> dict[str, Any]:
    if not metricas_nvidia:
        return metricas_ollama

    if not metricas_ollama:
        return metricas_nvidia

    combinadas = dict(metricas_ollama)
    combinadas["nvidia"] = metricas_nvidia
    return combinadas


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
