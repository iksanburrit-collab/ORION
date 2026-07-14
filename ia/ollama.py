from __future__ import annotations

import json
import socket
import time
from typing import Any
from urllib import error, request

from ia.contratos import RespuestaIA, SolicitudIA
from ia.prompts import construir_prompt_sistema


OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO_PREDETERMINADO = "qwen3:1.7b"
ERROR_OLLAMA = "No pude usar Ollama:"


def responder(solicitud: SolicitudIA) -> RespuestaIA:
    inicio = time.perf_counter()
    modelo = solicitud.modelo or MODELO_PREDETERMINADO
    opciones = solicitud.opciones

    payload = _crear_payload(
        solicitud.mensaje,
        solicitud.contexto,
        solicitud.historial,
        modelo,
        str(opciones.get("keep_alive", "10m") or "10m"),
        int(opciones.get("num_predict", solicitud.limite_salida or 100)),
        int(opciones.get("num_ctx", 2048)),
    )
    datos = json.dumps(payload).encode("utf-8")
    peticion = request.Request(
        OLLAMA_URL,
        data=datos,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(peticion, timeout=solicitud.timeout) as respuesta:
            cuerpo = respuesta.read().decode("utf-8")
            codigo_estado = _codigo_estado(respuesta)
    except error.HTTPError as exc:
        return _respuesta_http(exc, modelo, inicio)
    except (TimeoutError, socket.timeout):
        return _respuesta_error(
            "la respuesta tardo demasiado.",
            modelo,
            "timeout",
            inicio,
            codigo_estado="Timeout",
        )
    except (error.URLError, ConnectionError, OSError) as exc:
        return _respuesta_error(
            _mensaje_conexion_sin_prefijo(exc),
            modelo,
            "sin_conexion",
            inicio,
        )

    try:
        datos_respuesta = json.loads(cuerpo)
    except json.JSONDecodeError:
        return _respuesta_error(
            "Ollama devolvio JSON invalido.",
            modelo,
            "json_invalido",
            inicio,
            codigo_estado=codigo_estado,
        )

    if not isinstance(datos_respuesta, dict):
        return _respuesta_error(
            "Ollama devolvio una respuesta invalida.",
            modelo,
            "formato_inesperado",
            inicio,
            codigo_estado=codigo_estado,
        )

    if datos_respuesta.get("error"):
        return _respuesta_error_modelo(
            str(datos_respuesta["error"]),
            modelo,
            inicio,
            codigo_estado,
        )

    contenido = datos_respuesta.get("message", {}).get("content", "")

    if not isinstance(contenido, str) or not contenido.strip():
        return _respuesta_error(
            "Ollama devolvio una respuesta vacia.",
            modelo,
            "respuesta_vacia",
            inicio,
            codigo_estado=codigo_estado,
        )

    return RespuestaIA(
        texto=_limitar_respuesta(contenido.strip(), solicitud.limite_salida * 8),
        proveedor="ollama",
        modelo=modelo,
        error=False,
        latencia=_latencia(inicio),
        codigo_estado=codigo_estado,
        diagnostico={"endpoint": OLLAMA_URL},
    )


def generar_respuesta(
    mensaje: str,
    contexto: str = "",
    historial: list[dict[str, str]] | None = None,
    modelo: str = MODELO_PREDETERMINADO,
    timeout: float = 60.0,
    keep_alive: str = "10m",
    limite_respuesta: int = 1200,
    num_predict: int = 100,
    num_ctx: int = 2048,
) -> str:
    solicitud = SolicitudIA(
        mensaje,
        contexto,
        historial,
        modelo,
        timeout,
        num_predict,
        {
            "keep_alive": keep_alive,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
    )
    respuesta = responder(solicitud)

    if respuesta.error:
        return respuesta.texto

    return _limitar_respuesta(respuesta.texto, limite_respuesta)


def _crear_payload(
    mensaje: str,
    contexto: str,
    historial: list[dict[str, str]] | None,
    modelo: str,
    keep_alive: str,
    num_predict: int,
    num_ctx: int,
) -> dict[str, Any]:
    mensajes = [
        {
            "role": "system",
            "content": construir_prompt_sistema(contexto),
        }
    ]

    for entrada in historial or []:
        if not isinstance(entrada, dict):
            continue

        role = entrada.get("role")
        content = entrada.get("content")

        if role in {"user", "assistant"} and isinstance(content, str):
            mensajes.append({"role": role, "content": content})

    mensajes.append({"role": "user", "content": mensaje})

    return {
        "model": modelo or MODELO_PREDETERMINADO,
        "messages": mensajes,
        "stream": False,
        "think": False,
        "keep_alive": keep_alive or "10m",
        "options": {
            "num_predict": max(1, int(num_predict)),
            "num_ctx": max(512, int(num_ctx)),
        },
    }


def _mensaje_error_http(exc: error.HTTPError) -> str:
    detalle = ""

    try:
        cuerpo = exc.read().decode("utf-8")
        datos = json.loads(cuerpo)

        if isinstance(datos, dict):
            detalle = str(datos.get("error", ""))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        detalle = ""

    if exc.code == 404 or "model" in detalle.lower():
        return (
            f"{ERROR_OLLAMA} el modelo no esta instalado "
            "o no fue encontrado."
        )

    return f"{ERROR_OLLAMA} Ollama respondio con HTTP {exc.code}."


def _mensaje_error_conexion(exc: BaseException) -> str:
    return f"{ERROR_OLLAMA} {_mensaje_conexion_sin_prefijo(exc)}"


def _mensaje_conexion_sin_prefijo(exc: BaseException) -> str:
    razon = str(exc).lower()

    if "timed out" in razon or "timeout" in razon:
        return "la respuesta tardo demasiado."

    return "no pude conectar con el servicio local."


def _mensaje_error_modelo(detalle: str) -> str:
    detalle_normalizado = detalle.lower()

    if "model" in detalle_normalizado or "pull" in detalle_normalizado:
        return (
            f"{ERROR_OLLAMA} el modelo no esta instalado "
            "o no fue encontrado."
        )

    return f"{ERROR_OLLAMA} {detalle.strip() or 'respuesta invalida'}."


def _limitar_respuesta(texto: str, limite: int = 1200) -> str:
    if len(texto) <= limite:
        return texto

    return texto[:limite].rstrip() + "..."


def _respuesta_http(exc: error.HTTPError, modelo: str, inicio: float) -> RespuestaIA:
    texto = _mensaje_error_http(exc)
    tipo_error = "http_error"

    if exc.code == 404 or "modelo no esta instalado" in texto:
        tipo_error = "modelo_no_disponible"

    return RespuestaIA(
        texto=texto,
        proveedor="ollama",
        modelo=modelo,
        error=True,
        tipo_error=tipo_error,
        latencia=_latencia(inicio),
        codigo_estado=exc.code,
        diagnostico={"endpoint": OLLAMA_URL},
    )


def _respuesta_error(
    mensaje: str,
    modelo: str,
    tipo_error: str,
    inicio: float,
    codigo_estado: int | str | None = None,
) -> RespuestaIA:
    return RespuestaIA(
        texto=f"{ERROR_OLLAMA} {mensaje}",
        proveedor="ollama",
        modelo=modelo,
        error=True,
        tipo_error=tipo_error,
        latencia=_latencia(inicio),
        codigo_estado=codigo_estado,
        diagnostico={"endpoint": OLLAMA_URL},
    )


def _respuesta_error_modelo(
    detalle: str,
    modelo: str,
    inicio: float,
    codigo_estado: int | str | None,
) -> RespuestaIA:
    texto = _mensaje_error_modelo(detalle)
    tipo_error = "modelo_no_disponible"

    if "modelo no esta instalado" not in texto:
        tipo_error = "respuesta_invalida"

    return RespuestaIA(
        texto=texto,
        proveedor="ollama",
        modelo=modelo,
        error=True,
        tipo_error=tipo_error,
        latencia=_latencia(inicio),
        codigo_estado=codigo_estado,
        diagnostico={"endpoint": OLLAMA_URL},
    )


def _latencia(inicio: float) -> float:
    return round(time.perf_counter() - inicio, 4)


def _codigo_estado(respuesta: Any) -> int | str | None:
    codigo = getattr(respuesta, "status", None)

    if codigo is not None:
        return codigo

    getcode = getattr(respuesta, "getcode", None)

    if callable(getcode):
        return getcode()

    return None
