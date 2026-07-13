from __future__ import annotations

import json
import socket
from typing import Any
from urllib import error, request

from ia.prompts import construir_prompt_sistema


OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO_PREDETERMINADO = "qwen3:1.7b"
ERROR_OLLAMA = "No pude usar Ollama:"


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
    payload = _crear_payload(
        mensaje,
        contexto,
        historial,
        modelo,
        keep_alive,
        num_predict,
        num_ctx,
    )
    datos = json.dumps(payload).encode("utf-8")
    solicitud = request.Request(
        OLLAMA_URL,
        data=datos,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(solicitud, timeout=timeout) as respuesta:
            cuerpo = respuesta.read().decode("utf-8")
    except error.HTTPError as exc:
        return _mensaje_error_http(exc)
    except (TimeoutError, socket.timeout):
        return f"{ERROR_OLLAMA} la respuesta tardo demasiado."
    except (error.URLError, ConnectionError, OSError) as exc:
        return _mensaje_error_conexion(exc)

    try:
        datos_respuesta = json.loads(cuerpo)
    except json.JSONDecodeError:
        return f"{ERROR_OLLAMA} Ollama devolvio JSON invalido."

    if not isinstance(datos_respuesta, dict):
        return f"{ERROR_OLLAMA} Ollama devolvio una respuesta invalida."

    if datos_respuesta.get("error"):
        return _mensaje_error_modelo(str(datos_respuesta["error"]))

    contenido = (
        datos_respuesta
        .get("message", {})
        .get("content", "")
    )

    if not isinstance(contenido, str) or not contenido.strip():
        return f"{ERROR_OLLAMA} Ollama devolvio una respuesta vacia."

    return _limitar_respuesta(contenido.strip(), limite_respuesta)


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
    razon = str(exc).lower()

    if "timed out" in razon or "timeout" in razon:
        return f"{ERROR_OLLAMA} la respuesta tardo demasiado."

    return f"{ERROR_OLLAMA} no pude conectar con el servicio local."


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
