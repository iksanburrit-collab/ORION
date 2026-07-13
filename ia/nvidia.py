from __future__ import annotations

import json
import os
import socket
from typing import Any
from urllib import error, request

from ia.prompts import construir_prompt_sistema


NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELO_PREDETERMINADO = "meta/llama-4-maverick-17b-128e-instruct"
ERROR_NVIDIA = "No pude usar NVIDIA Cloud:"


def generar_respuesta_nvidia(
    mensaje: str,
    contexto: str = "",
    historial: list[dict[str, str]] | None = None,
    modelo: str = MODELO_PREDETERMINADO,
    timeout: float = 25.0,
    max_tokens: int = 180,
) -> str:
    api_key = os.getenv("NVIDIA_API_KEY")

    if not api_key:
        return f"{ERROR_NVIDIA} falta configurar NVIDIA_API_KEY."

    payload = _crear_payload(
        mensaje,
        contexto,
        historial,
        modelo,
        max_tokens,
    )
    datos = json.dumps(payload).encode("utf-8")
    solicitud = request.Request(
        NVIDIA_URL,
        data=datos,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(solicitud, timeout=timeout) as respuesta:
            cuerpo = respuesta.read().decode("utf-8")
    except error.HTTPError as exc:
        return _mensaje_error_http(exc)
    except (TimeoutError, socket.timeout):
        return f"{ERROR_NVIDIA} la respuesta tardo demasiado."
    except (error.URLError, ConnectionError, OSError):
        return f"{ERROR_NVIDIA} no pude conectar con el servicio."

    try:
        datos_respuesta = json.loads(cuerpo)
    except json.JSONDecodeError:
        return f"{ERROR_NVIDIA} la respuesta no fue JSON valido."

    contenido = _extraer_contenido(datos_respuesta)

    if not contenido:
        return f"{ERROR_NVIDIA} NVIDIA devolvio una respuesta vacia."

    return contenido


def _crear_payload(
    mensaje: str,
    contexto: str,
    historial: list[dict[str, str]] | None,
    modelo: str,
    max_tokens: int,
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
        "temperature": 0.6,
        "top_p": 0.9,
        "max_tokens": max(1, int(max_tokens)),
        "stream": False,
    }


def _extraer_contenido(datos: Any) -> str:
    if not isinstance(datos, dict):
        return ""

    choices = datos.get("choices", [])

    if not isinstance(choices, list) or not choices:
        return ""

    choice = choices[0]

    if not isinstance(choice, dict):
        return ""

    message = choice.get("message", {})

    if not isinstance(message, dict):
        return ""

    content = message.get("content", "")

    if not isinstance(content, str):
        return ""

    return content.strip()


def _mensaje_error_http(exc: error.HTTPError) -> str:
    if exc.code == 401:
        return f"{ERROR_NVIDIA} credenciales invalidas."

    if exc.code in {402, 403}:
        return f"{ERROR_NVIDIA} la cuenta no tiene acceso suficiente."

    if exc.code == 429:
        return f"{ERROR_NVIDIA} limite de uso alcanzado."

    if 500 <= exc.code <= 599:
        return f"{ERROR_NVIDIA} el servicio tuvo un problema temporal."

    return f"{ERROR_NVIDIA} NVIDIA respondio con HTTP {exc.code}."
