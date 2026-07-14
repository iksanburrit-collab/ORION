from __future__ import annotations

from dataclasses import dataclass
import json
import os
import socket
import time
from typing import Any
from urllib import error, request

from ia.prompts import construir_prompt_sistema


NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELO_PREDETERMINADO = "meta/llama-4-maverick-17b-128e-instruct"
ERROR_NVIDIA = "No pude usar NVIDIA Cloud:"


@dataclass(frozen=True)
class DiagnosticoNvidia:
    texto: str
    endpoint: str
    modelo: str
    api_detectada: bool
    http: int | str | None
    mensaje: str
    tiempo: float
    timeout: float


def generar_respuesta_nvidia(
    mensaje: str,
    contexto: str = "",
    historial: list[dict[str, str]] | None = None,
    modelo: str = MODELO_PREDETERMINADO,
    timeout: float = 25.0,
    max_tokens: int = 180,
) -> str | DiagnosticoNvidia:
    return _generar_respuesta_nvidia(
        mensaje,
        contexto=contexto,
        historial=historial,
        modelo=modelo,
        timeout=timeout,
        max_tokens=max_tokens,
        diagnostico=False,
    )


def generar_respuesta_nvidia_diagnostico(
    mensaje: str,
    contexto: str = "",
    historial: list[dict[str, str]] | None = None,
    modelo: str = MODELO_PREDETERMINADO,
    timeout: float = 25.0,
    max_tokens: int = 180,
) -> DiagnosticoNvidia:
    return _generar_respuesta_nvidia(
        mensaje,
        contexto=contexto,
        historial=historial,
        modelo=modelo,
        timeout=timeout,
        max_tokens=max_tokens,
        diagnostico=True,
    )


def _generar_respuesta_nvidia(
    mensaje: str,
    contexto: str = "",
    historial: list[dict[str, str]] | None = None,
    modelo: str = MODELO_PREDETERMINADO,
    timeout: float = 25.0,
    max_tokens: int = 180,
    diagnostico: bool = False,
) -> str | DiagnosticoNvidia:
    inicio = time.perf_counter()
    api_key = os.getenv("NVIDIA_API_KEY")
    modelo_usado = modelo or MODELO_PREDETERMINADO

    if not api_key:
        return _resultado(
            f"{ERROR_NVIDIA} falta configurar NVIDIA_API_KEY.",
            modelo_usado,
            False,
            None,
            "falta configurar NVIDIA_API_KEY",
            inicio,
            timeout,
            diagnostico,
        )

    payload = _crear_payload(
        mensaje,
        contexto,
        historial,
        modelo_usado,
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
            http = getattr(respuesta, "status", None) or respuesta.getcode()
    except error.HTTPError as exc:
        mensaje_error, detalle = _mensaje_error_http(exc)
        return _resultado(
            mensaje_error,
            modelo_usado,
            True,
            exc.code,
            detalle,
            inicio,
            timeout,
            diagnostico,
        )
    except (TimeoutError, socket.timeout):
        return _resultado(
            f"{ERROR_NVIDIA} la respuesta tardo demasiado.",
            modelo_usado,
            True,
            "Timeout",
            "timeout",
            inicio,
            timeout,
            diagnostico,
        )
    except error.URLError as exc:
        if _es_timeout(exc):
            return _resultado(
                f"{ERROR_NVIDIA} la respuesta tardo demasiado.",
                modelo_usado,
                True,
                "Timeout",
                "timeout",
                inicio,
                timeout,
                diagnostico,
            )

        return _resultado(
            f"{ERROR_NVIDIA} no pude conectar con el servicio.",
            modelo_usado,
            True,
            None,
            str(exc.reason),
            inicio,
            timeout,
            diagnostico,
        )
    except (ConnectionError, OSError) as exc:
        return _resultado(
            f"{ERROR_NVIDIA} no pude conectar con el servicio.",
            modelo_usado,
            True,
            None,
            str(exc),
            inicio,
            timeout,
            diagnostico,
        )

    try:
        datos_respuesta = json.loads(cuerpo)
    except json.JSONDecodeError:
        return _resultado(
            f"{ERROR_NVIDIA} la respuesta no fue JSON valido.",
            modelo_usado,
            True,
            http,
            "JSON invalido",
            inicio,
            timeout,
            diagnostico,
        )

    contenido = _extraer_contenido(datos_respuesta)

    if not contenido:
        return _resultado(
            f"{ERROR_NVIDIA} NVIDIA devolvio una respuesta vacia.",
            modelo_usado,
            True,
            http,
            "respuesta vacia",
            inicio,
            timeout,
            diagnostico,
        )

    return _resultado(
        contenido,
        modelo_usado,
        True,
        http,
        "OK",
        inicio,
        timeout,
        diagnostico,
    )


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


def _mensaje_error_http(exc: error.HTTPError) -> tuple[str, str]:
    detalle = _leer_detalle_http(exc)

    if exc.code == 401:
        return f"{ERROR_NVIDIA} credenciales invalidas. HTTP 401. {detalle}".strip(), detalle

    if exc.code in {402, 403}:
        return (
            f"{ERROR_NVIDIA} la cuenta no tiene acceso suficiente. "
            f"HTTP {exc.code}. {detalle}"
        ).strip(), detalle

    if exc.code == 429:
        return f"{ERROR_NVIDIA} limite de uso alcanzado. HTTP 429. {detalle}".strip(), detalle

    if 500 <= exc.code <= 599:
        return (
            f"{ERROR_NVIDIA} el servicio tuvo un problema temporal. "
            f"HTTP {exc.code}. {detalle}"
        ).strip(), detalle

    return (
        f"{ERROR_NVIDIA} NVIDIA respondio con HTTP {exc.code}. {detalle}"
    ).strip(), detalle


def _leer_detalle_http(exc: error.HTTPError) -> str:
    try:
        cuerpo = exc.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return str(getattr(exc, "reason", "") or "")

    try:
        datos = json.loads(cuerpo)
    except json.JSONDecodeError:
        return cuerpo[:300]

    if not isinstance(datos, dict):
        return cuerpo[:300]

    detalle = datos.get("error") or datos.get("message") or datos

    if isinstance(detalle, dict):
        detalle = detalle.get("message") or detalle.get("detail") or detalle

    return str(detalle)[:300]


def _es_timeout(exc: error.URLError) -> bool:
    razon = getattr(exc, "reason", None)

    if isinstance(razon, socket.timeout):
        return True

    return "timed out" in str(razon).lower() or "timeout" in str(razon).lower()


def _resultado(
    texto: str,
    modelo: str,
    api_detectada: bool,
    http: int | str | None,
    mensaje: str,
    inicio: float,
    timeout: float,
    diagnostico: bool,
) -> str | DiagnosticoNvidia:
    if not diagnostico:
        return texto

    return DiagnosticoNvidia(
        texto=texto,
        endpoint=NVIDIA_URL,
        modelo=modelo,
        api_detectada=api_detectada,
        http=http,
        mensaje=mensaje,
        tiempo=round(time.perf_counter() - inicio, 4),
        timeout=timeout,
    )
