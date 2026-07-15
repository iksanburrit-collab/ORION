from __future__ import annotations

import json
import os
import socket
import time
from typing import Any
from urllib import error, request

from ia.contratos import RespuestaIA, SolicitudIA
from ia.prompts import construir_prompt_sistema


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
PROVEEDOR = "groq"
MODELO_PREDETERMINADO = "llama-3.1-8b-instant"


def responder(solicitud: SolicitudIA) -> RespuestaIA:
    inicio = time.perf_counter()
    modelo = solicitud.modelo or MODELO_PREDETERMINADO
    api_key = os.getenv("GROQ_API_KEY")
    debug = _debug_habilitado(solicitud)

    if not api_key:
        return _respuesta_error(
            "Falta configurar GROQ_API_KEY.",
            modelo,
            "api_key_ausente",
            inicio,
        )

    payload = _crear_payload(solicitud, modelo)
    datos = json.dumps(payload).encode("utf-8")
    peticion = request.Request(
        GROQ_URL,
        data=datos,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ORION/2.0 Python",
        },
        method="POST",
    )

    try:
        with request.urlopen(peticion, timeout=solicitud.timeout) as respuesta:
            cuerpo = respuesta.read().decode("utf-8")
            codigo_estado = _codigo_estado(respuesta)
    except error.HTTPError as exc:
        return _respuesta_http(exc, modelo, inicio, debug)
    except (TimeoutError, socket.timeout):
        return _respuesta_error(
            "Groq tardo demasiado en responder.",
            modelo,
            "timeout",
            inicio,
            codigo_estado="Timeout",
        )
    except error.URLError as exc:
        if _es_timeout(exc):
            return _respuesta_error(
                "Groq tardo demasiado en responder.",
                modelo,
                "timeout",
                inicio,
                codigo_estado="Timeout",
            )

        return _respuesta_error(
            "No pude conectar con Groq.",
            modelo,
            "sin_conexion",
            inicio,
            diagnostico={"detalle": _detalle_seguro(getattr(exc, "reason", ""))},
        )
    except (ConnectionError, OSError) as exc:
        return _respuesta_error(
            "No pude conectar con Groq.",
            modelo,
            "sin_conexion",
            inicio,
            diagnostico={"detalle": _detalle_seguro(exc)},
        )

    try:
        datos_respuesta = json.loads(cuerpo)
    except json.JSONDecodeError:
        return _respuesta_error(
            "Groq devolvio JSON invalido.",
            modelo,
            "json_invalido",
            inicio,
            codigo_estado=codigo_estado,
        )

    contenido = _extraer_contenido(datos_respuesta)

    if contenido is None:
        return _respuesta_error(
            "Groq devolvio un formato inesperado.",
            modelo,
            "formato_inesperado",
            inicio,
            codigo_estado=codigo_estado,
        )

    if not contenido.strip():
        return _respuesta_error(
            "Groq devolvio una respuesta vacia.",
            modelo,
            "respuesta_vacia",
            inicio,
            codigo_estado=codigo_estado,
        )

    return RespuestaIA(
        texto=contenido.strip(),
        proveedor=PROVEEDOR,
        modelo=modelo,
        error=False,
        latencia=_latencia(inicio),
        codigo_estado=codigo_estado,
        diagnostico={"endpoint": GROQ_URL},
    )


def _crear_payload(solicitud: SolicitudIA, modelo: str) -> dict[str, Any]:
    mensajes = [
        {
            "role": "system",
            "content": construir_prompt_sistema(solicitud.contexto),
        }
    ]

    for entrada in solicitud.historial or []:
        if not isinstance(entrada, dict):
            continue

        role = entrada.get("role")
        content = entrada.get("content")

        if role in {"user", "assistant"} and isinstance(content, str):
            mensajes.append({"role": role, "content": content})

    mensajes.append({"role": "user", "content": solicitud.mensaje})

    return {
        "model": modelo,
        "messages": mensajes,
        "temperature": float(solicitud.opciones.get("temperature", 0.6)),
        "top_p": float(solicitud.opciones.get("top_p", 0.9)),
        "max_completion_tokens": max(1, int(solicitud.limite_salida)),
        "stream": False,
    }


def _extraer_contenido(datos: Any) -> str | None:
    if not isinstance(datos, dict):
        return None

    choices = datos.get("choices")

    if not isinstance(choices, list) or not choices:
        return None

    choice = choices[0]

    if not isinstance(choice, dict):
        return None

    message = choice.get("message")

    if not isinstance(message, dict):
        return None

    content = message.get("content")

    if not isinstance(content, str):
        return None

    return content


def _respuesta_http(
    exc: error.HTTPError,
    modelo: str,
    inicio: float,
    debug: bool,
) -> RespuestaIA:
    cuerpo_json, mensaje_groq = _leer_error_http(exc)
    tipo_error = f"http_{exc.code}"
    mensaje = mensaje_groq or f"HTTP {exc.code}"

    if exc.code == 401:
        tipo_error = "credenciales_invalidas"
    elif exc.code == 402:
        tipo_error = "pago_requerido"
    elif exc.code == 403:
        tipo_error = "http_403"
    elif exc.code == 404:
        tipo_error = "modelo_no_disponible"
    elif exc.code == 429:
        tipo_error = "limite_uso"
    elif 500 <= exc.code <= 599:
        tipo_error = "servicio_temporal"

    if tipo_error.startswith("http_") and "model" in mensaje.lower():
        tipo_error = "modelo_no_disponible"

    diagnostico = {
        "cuerpo_error": cuerpo_json,
        "mensaje_groq": mensaje_groq,
    }

    return _respuesta_error(
        mensaje,
        modelo,
        tipo_error,
        inicio,
        codigo_estado=exc.code,
        diagnostico=diagnostico,
    )


def _respuesta_error(
    texto: str,
    modelo: str,
    tipo_error: str,
    inicio: float,
    codigo_estado: int | str | None = None,
    diagnostico: dict[str, Any] | None = None,
) -> RespuestaIA:
    datos_diagnostico = {"endpoint": GROQ_URL}
    datos_diagnostico.update(diagnostico or {})

    return RespuestaIA(
        texto=f"No pude usar Groq: {texto}",
        proveedor=PROVEEDOR,
        modelo=modelo,
        error=True,
        tipo_error=tipo_error,
        latencia=_latencia(inicio),
        codigo_estado=codigo_estado,
        diagnostico=datos_diagnostico,
    )


def _leer_error_http(exc: error.HTTPError) -> tuple[Any, str]:
    try:
        cuerpo = exc.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        detalle = str(getattr(exc, "reason", "") or "")
        return detalle, detalle

    try:
        datos = json.loads(cuerpo)
    except json.JSONDecodeError:
        detalle = _detalle_seguro(cuerpo)
        return detalle, detalle

    datos = _sanitizar_json(datos)
    mensaje = _extraer_mensaje_error(datos)

    return datos, mensaje


def _extraer_mensaje_error(datos: Any) -> str:
    if not isinstance(datos, dict):
        return _detalle_seguro(datos)

    detalle = datos.get("error") or datos.get("message") or datos

    if isinstance(detalle, dict):
        mensaje = detalle.get("message") or detalle.get("detail") or detalle
    else:
        mensaje = detalle

    return _detalle_seguro(mensaje)


def _sanitizar_json(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {
            str(clave): _sanitizar_json(subvalor)
            for clave, subvalor in valor.items()
        }

    if isinstance(valor, list):
        return [_sanitizar_json(subvalor) for subvalor in valor]

    if isinstance(valor, str):
        return _detalle_seguro(valor)

    return valor


def _es_timeout(exc: error.URLError) -> bool:
    razon = getattr(exc, "reason", None)

    if isinstance(razon, socket.timeout):
        return True

    return "timed out" in str(razon).lower() or "timeout" in str(razon).lower()


def _detalle_seguro(valor: Any) -> str:
    texto = str(valor)
    api_key = os.getenv("GROQ_API_KEY")

    if api_key:
        texto = texto.replace(api_key, "[oculto]")

    return texto[:300]


def _debug_habilitado(solicitud: SolicitudIA) -> bool:
    return bool(solicitud.opciones.get("debug_rendimiento", False))


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
