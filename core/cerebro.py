from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Callable

from comandos.calculadora import ejecutar_calculadora
from comandos.navegador import navegador_inteligente
from comandos.sistema import mostrar_ayuda, mostrar_perfil
from core.handlers.alias import procesar_alias
from core.handlers.configuracion import procesar_configuracion
from core.handlers.memoria import procesar_memoria
from core.handlers.notas import procesar_notas
from core.intenciones import detectar_intencion
from core.memoria import (
    actualizar_perfil,
    agregar_historial,
    aprender,
    construir_contexto_para_ia,
    guardar_contexto,
    guardar_memoria,
    obtener_historial_conversacion,
    obtener_fecha_nacimiento,
    obtener_nombre,
    registrar_turno_conversacion,
)
from core.personalidad import responder_personalidad
from ia.ollama import ERROR_OLLAMA, generar_respuesta
from utilidades.fechas import calcular_edad, fecha_actual, hora_actual


GuardarFunc = Callable[[], None]


@dataclass
class ResultadoCerebro:
    texto: str
    intencion: str
    accion: str = ""
    respuesta: str = ""
    salir: bool = False
    solicitud: str | None = None
    conocimiento: Any | None = None

    def como_dict(self) -> dict[str, Any]:
        return {
            "texto": self.texto,
            "intencion": self.intencion,
            "accion": self.accion,
            "respuesta": self.respuesta,
            "salir": self.salir,
            "solicitud": self.solicitud,
            "conocimiento": self.conocimiento,
        }


def procesar(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    notas: list[str] | None = None,
    alias: dict[str, str] | None = None,
    recordatorios: list[str] | None = None,
    guardar_notas: GuardarFunc | None = None,
    guardar_alias: GuardarFunc | None = None,
    guardar_config: GuardarFunc | None = None,
) -> ResultadoCerebro:

    notas = notas if notas is not None else []
    alias = alias if alias is not None else {}
    recordatorios = recordatorios if recordatorios is not None else []

    intencion = detectar_intencion(texto)

    resultado = ResultadoCerebro(
        texto=texto,
        intencion=intencion,
    )

    if navegador_inteligente(texto):
        resultado.intencion = "navegador"
        resultado.accion = "navegador"
        return resultado

    if _resolver_comando_directo(
        texto,
        memoria,
        config,
        notas,
        alias,
        recordatorios,
        guardar_notas,
        guardar_alias,
        guardar_config,
        resultado,
    ):
        return resultado

    conocimiento = _registrar_aprendizaje(texto, memoria)
    resultado.conocimiento = conocimiento

    if conocimiento is not None:
        resultado.accion = "aprendizaje"

        if conocimiento.tipo == "gusto":
            mensaje = (
                f"Entendido. Recordaré que te gusta "
                f"{conocimiento.valor} en {conocimiento.categoria}."
            )

        elif conocimiento.tipo == "aprendizaje":
            mensaje = (
                f"Entendido. Recordaré que estás aprendiendo "
                f"{conocimiento.valor} en {conocimiento.categoria}."
            )

        elif conocimiento.tipo == "objetivo":
            mensaje = (
                f"Objetivo guardado: {conocimiento.valor}."
            )

        else:
            mensaje = (
                f"Información guardada: {conocimiento.valor}."
            )

        resultado.respuesta = responder_personalidad(
            mensaje,
            config,
        )

        return resultado

    if _resolver_intencion(
        texto,
        intencion,
        memoria,
        config,
        resultado,
    ):
        return resultado

    if _resolver_consulta_memoria(texto, memoria, config, resultado):
        return resultado

    if _resolver_ia(texto, memoria, config, resultado):
        return resultado

    resultado.respuesta = random.choice([
        "No entendí 🤔",
        "Explícame diferente 😄",
    ])

    resultado.accion = "desconocido"

    return resultado

def completar_solicitud(
    solicitud: str,
    valor: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
) -> ResultadoCerebro:
    """Completa una solicitud que requiere datos adicionales del usuario."""
    valor = valor.strip()

    if not valor:
        return ResultadoCerebro(
            texto=valor,
            intencion=solicitud,
            accion="solicitud_invalida",
            respuesta="El valor no puede estar vacío.",
        )

    if solicitud == "nombre":
        actualizar_perfil(memoria, nombre=valor)
        guardar_memoria(memoria)
        return ResultadoCerebro(
            texto=valor,
            intencion="nombre",
            accion="actualizar_nombre",
            respuesta="Guardado 👍",
        )

    if solicitud == "fecha_nacimiento":
        actualizar_perfil(memoria, fecha_nacimiento=valor)
        guardar_memoria(memoria)
        return ResultadoCerebro(
            texto=valor,
            intencion="cumple",
            accion="actualizar_cumple",
            respuesta="Guardado 👍",
        )

    return ResultadoCerebro(
        texto=valor,
        intencion=solicitud,
        accion="solicitud_desconocida",
        respuesta="No pude completar esa solicitud.",
    )


def _registrar_aprendizaje(
    texto: str,
    memoria: dict[str, Any]
) -> Any | None:
    conocimiento = aprender(texto, memoria, guardar=False)

    if conocimiento is not None:
        agregar_historial(texto, memoria, guardar=False)
        guardar_contexto(texto, memoria, guardar=False)
        guardar_memoria(memoria)

    return conocimiento


def _resolver_ia(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    resultado: ResultadoCerebro,
) -> bool:
    config_ia = _config_ia(config)

    if not config_ia["activada"]:
        return False

    contexto = construir_contexto_para_ia(
        memoria,
        consulta=texto,
        limite=config_ia["limite_contexto"],
    )
    historial = obtener_historial_conversacion(
        memoria,
        limite=config_ia["max_turnos_conversacion"],
    )
    respuesta = generar_respuesta(
        texto,
        contexto=contexto,
        historial=historial,
        modelo=config_ia["modelo"],
        timeout=config_ia["timeout"],
        keep_alive=config_ia["keep_alive"],
        limite_respuesta=config_ia["longitud_respuesta"],
    )

    resultado.respuesta = respuesta
    resultado.accion = (
        "error_ia"
        if respuesta.startswith(ERROR_OLLAMA)
        else "respuesta_ia"
    )

    if resultado.accion == "respuesta_ia":
        registrar_turno_conversacion(
            memoria,
            texto,
            respuesta,
            limite=config_ia["max_turnos_conversacion"],
        )
        guardar_memoria(memoria)

    return True


def _config_ia(config: dict[str, Any]) -> dict[str, Any]:
    ia = config.get("ia", {})

    if not isinstance(ia, dict):
        ia = {}

    return {
        "activada": bool(ia.get("activada", True)),
        "modelo": str(ia.get("modelo", "qwen3:1.7b") or "qwen3:1.7b"),
        "timeout": _numero_config(ia.get("timeout"), 60.0),
        "limite_contexto": int(_numero_config(
            ia.get("limite_contexto"),
            1200.0,
        )),
        "max_turnos_conversacion": int(_numero_config(
            ia.get("max_turnos_conversacion"),
            6.0,
        )),
        "longitud_respuesta": int(_numero_config(
            ia.get("longitud_respuesta"),
            1200.0,
        )),
        "keep_alive": str(ia.get("keep_alive", "10m") or "10m"),
    }


def _numero_config(valor: Any, defecto: float) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return defecto

    return numero if numero > 0 else defecto


def _resolver_intencion(
    texto: str,
    intencion: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    resultado: ResultadoCerebro,
) -> bool:
    nombre = obtener_nombre(memoria)
    fecha_nacimiento = obtener_fecha_nacimiento(memoria)
    edad = calcular_edad(fecha_nacimiento)

    if intencion == "saludo":
        respuesta = f"Hola {nombre} 👋" if nombre else "Hola 👋"
        resultado.respuesta = responder_personalidad(respuesta, config)
        resultado.accion = "saludar"
        return True

    if intencion == "nombre":
        resultado.respuesta = "Escribe tu nombre:"
        resultado.solicitud = "nombre"
        resultado.accion = "solicitar_nombre"
        return True

    if intencion == "cumple":
        resultado.respuesta = "Escribe tu fecha de nacimiento (YYYY-MM-DD):"
        resultado.solicitud = "fecha_nacimiento"
        resultado.accion = "solicitar_cumple"
        return True

    if intencion == "perfil":
        resultado.respuesta = mostrar_perfil(nombre, edad)
        resultado.accion = "mostrar_perfil"
        return True

    if intencion == "edad":
        respuesta = f"Tienes {edad} años" if edad else "No sé tu edad 😅"
        resultado.respuesta = responder_personalidad(respuesta, config)
        resultado.accion = "mostrar_edad"
        return True

    if intencion == "hora":
        resultado.respuesta = responder_personalidad(hora_actual(), config)
        resultado.accion = "mostrar_hora"
        return True

    if intencion == "fecha":
        resultado.respuesta = responder_personalidad(fecha_actual(), config)
        resultado.accion = "mostrar_fecha"
        return True

    if intencion == "estado":
        respuesta = random.choice([
            "Estoy bien",
            "Todo cool 😎",
            "Todo en orden 👍",
            "Procesando datos 🤖",
        ])
        resultado.respuesta = responder_personalidad(respuesta, config)
        resultado.accion = "mostrar_estado"
        return True

    if intencion == "calc":
        resultado.respuesta = ejecutar_calculadora(texto)
        resultado.accion = "calcular"
        return True

    if intencion == "version":
        resultado.respuesta = responder_personalidad("ORION v1.8", config)
        resultado.accion = "mostrar_version"
        return True

    if intencion == "ayuda":
        resultado.respuesta = mostrar_ayuda()
        resultado.accion = "mostrar_ayuda"
        return True

    if intencion == "salir":
        resultado.respuesta = "Apagando ORION 👋"
        resultado.accion = "salir"
        resultado.salir = True
        return True

    return False


def _resolver_comando_directo(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    notas: list[str],
    alias: dict[str, str],
    recordatorios: list[str],
    guardar_notas: GuardarFunc | None,
    guardar_alias: GuardarFunc | None,
    guardar_config: GuardarFunc | None,
    resultado: ResultadoCerebro,
) -> bool:
    del recordatorios

    if _aplicar_procesado(
        resultado,
        procesar_notas(texto, notas, guardar_notas=guardar_notas),
    ):
        return True

    if _aplicar_procesado(
        resultado,
        procesar_configuracion(texto, config, guardar_config=guardar_config),
    ):
        return True

    if _aplicar_procesado(
        resultado,
        procesar_alias(texto, alias, config, guardar_alias=guardar_alias),
    ):
        return True

    return False


def _resolver_consulta_memoria(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    resultado: ResultadoCerebro,
) -> bool:
    procesado, accion, respuesta = procesar_memoria(texto, memoria)

    if not procesado:
        return False

    resultado.accion = accion
    resultado.respuesta = responder_personalidad(respuesta, config)
    return True


def _aplicar_procesado(
    resultado: ResultadoCerebro,
    procesado: tuple[bool, str, str],
) -> bool:
    fue_procesado, accion, respuesta = procesado

    if not fue_procesado:
        return False

    resultado.accion = accion
    resultado.respuesta = respuesta
    return True
