from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Callable
from core.handlers.notas import procesar_notas
from comandos.calculadora import ejecutar_calculadora
from comandos.navegador import navegador_inteligente
from comandos.sistema import mostrar_ayuda, mostrar_perfil
from core.intenciones import detectar_intencion
from core.memoria import (
    actualizar_perfil,
    agregar_historial,
    aprender,
    guardar_contexto,
    guardar_memoria,
    obtener_fecha_nacimiento,
    obtener_nombre,
    obtener_ultimo_comando,
    obtener_ultimo_gusto,
)
from core.personalidad import responder_personalidad
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
) -> dict[str, Any]:
    """
    Punto central de decision de ORION.

    Toda entrada del usuario pasa por aqui: el cerebro registra contexto,
    detecta intenciones y coordina los modulos que ejecutan acciones.
    """

    notas = notas if notas is not None else []
    alias = alias if alias is not None else {}
    recordatorios = recordatorios if recordatorios is not None else []

    conocimiento = _registrar_entrada(texto, memoria)

    if navegador_inteligente(texto):
        return ResultadoCerebro(
            texto=texto,
            intencion="navegador",
            accion="navegador",
            conocimiento=conocimiento,
        ).como_dict()

    intencion = detectar_intencion(texto)
    resultado = ResultadoCerebro(
        texto=texto,
        intencion=intencion,
        conocimiento=conocimiento,
    )

    if _resolver_intencion(
        texto,
        intencion,
        memoria,
        config,
        resultado,
    ):
        return resultado.como_dict()

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
        return resultado.como_dict()

    resultado.respuesta = random.choice([
        "No entendí 🤔",
        "Explícame diferente 😄",
    ])
    resultado.accion = "desconocido"
    return resultado.como_dict()


def completar_solicitud(
    solicitud: str,
    valor: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Completa una solicitud que requiere datos adicionales del usuario."""
    valor = valor.strip()

    if not valor:
        return ResultadoCerebro(
            texto=valor,
            intencion=solicitud,
            accion="solicitud_invalida",
            respuesta="El valor no puede estar vacío.",
        ).como_dict()

    if solicitud == "nombre":
        actualizar_perfil(memoria, nombre=valor)
        guardar_memoria(memoria)
        return ResultadoCerebro(
            texto=valor,
            intencion="nombre",
            accion="actualizar_nombre",
            respuesta="Guardado 👍",
        ).como_dict()

    if solicitud == "fecha_nacimiento":
        actualizar_perfil(memoria, fecha_nacimiento=valor)
        guardar_memoria(memoria)
        return ResultadoCerebro(
            texto=valor,
            intencion="cumple",
            accion="actualizar_cumple",
            respuesta="Guardado 👍",
        ).como_dict()

    return ResultadoCerebro(
        texto=valor,
        intencion=solicitud,
        accion="solicitud_desconocida",
        respuesta="No pude completar esa solicitud.",
    ).como_dict()


def _registrar_entrada(
    texto: str,
    memoria: dict[str, Any]
) -> Any | None:
    conocimiento = aprender(texto, memoria, guardar=False)
    agregar_historial(texto, memoria, guardar=False)
    guardar_contexto(texto, memoria, guardar=False)
    guardar_memoria(memoria)
    return conocimiento


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
        responder_personalidad(
            f"Hola {nombre} 👋"
            if nombre
            else "Hola 👋",
            config,
        )
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
        mostrar_perfil(nombre, edad)
        resultado.accion = "mostrar_perfil"
        return True

    if intencion == "edad":
        responder_personalidad(
            f"Tienes {edad} años"
            if edad
            else "No sé tu edad 😅",
            config,
        )
        resultado.accion = "mostrar_edad"
        return True

    if intencion == "hora":
        responder_personalidad(hora_actual(), config)
        resultado.accion = "mostrar_hora"
        return True

    if intencion == "fecha":
        responder_personalidad(fecha_actual(), config)
        resultado.accion = "mostrar_fecha"
        return True

    if intencion == "estado":
        responder_personalidad(
            random.choice([
                "Estoy bien",
                "Todo cool 😎",
                "Todo en orden 👍",
                "Procesando datos 🤖",
            ]),
            config,
        )
        resultado.accion = "mostrar_estado"
        return True

    if intencion == "calc":
        ejecutar_calculadora(texto)
        resultado.accion = "calcular"
        return True

    if intencion == "version":
        responder_personalidad("ORION v1.8", config)
        resultado.accion = "mostrar_version"
        return True

    if intencion == "ayuda":
        mostrar_ayuda()
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
    
    procesado, accion, respuesta = procesar_notas(
        texto,
        notas,
        guardar_notas=guardar_notas,
    )
    if procesado:
        resultado.accion = accion
        resultado.respuesta = respuesta
        return True
    
    if texto.startswith("aprende:"):
        _guardar_alias(texto, alias, config, guardar_alias)
        resultado.accion = "guardar_alias"
        return True

    if texto in alias:
        responder_personalidad(alias[texto], config)
        resultado.accion = "ejecutar_alias"
        return True

    if texto.startswith("modo "):
        respuesta_modo = _cambiar_modo(texto, config, guardar_config)
        if respuesta_modo:
            resultado.respuesta = respuesta_modo
        resultado.accion = "cambiar_modo"
        return True

    if texto == "modo":
        resultado.respuesta = f"Modo actual: {config['modo']}"
        resultado.accion = "mostrar_modo"
        return True

    if "que hice" in texto:
        _recordar_ultimo_comando(memoria, config)
        resultado.accion = "recordar_ultimo_comando"
        return True

    if "que me gusta" in texto:
        _recordar_gusto(memoria, config)
        resultado.accion = "recordar_gusto"
        return True

    if "que recuerdas" in texto:
        responder_personalidad(
            f"Tengo {len(memoria['historial'])} recuerdos recientes",
            config,
        )
        resultado.accion = "contar_recuerdos"
        return True

    if "historial" in texto:
        respuesta_historial = _mostrar_historial(memoria, config)
        if respuesta_historial:
            resultado.respuesta = respuesta_historial
        resultado.accion = "mostrar_historial"
        return True

    return False


def _guardar_alias(
    texto: str,
    alias: dict[str, str],
    config: dict[str, Any],
    guardar_alias: GuardarFunc | None,
) -> None:
    try:
        contenido = texto.replace("aprende:", "", 1)
        clave, valor = contenido.split("=", 1)
        alias[clave.strip()] = valor.strip()
        _guardar(guardar_alias)
        responder_personalidad("Alias guardado 👍", config)
    except ValueError:
        responder_personalidad("Formato: aprende: comando=accion", config)


def _cambiar_modo(
    texto: str,
    config: dict[str, Any],
    guardar_config: GuardarFunc | None
) -> str | None:
    nuevo = texto.replace("modo ", "", 1)
    modos = ["normal", "ironman", "serio", "chill"]

    if nuevo in modos:
        config["modo"] = nuevo
        _guardar(guardar_config)
        responder_personalidad(f"Modo {nuevo} activado", config)
        return

    return "Modos disponibles: " + ", ".join(modos)


def _recordar_ultimo_comando(
    memoria: dict[str, Any],
    config: dict[str, Any]
) -> None:
    ultimo = obtener_ultimo_comando(memoria)

    if ultimo:
        responder_personalidad(f"La última orden fue: {ultimo}", config)
        return

    responder_personalidad("No recuerdo nada todavía", config)


def _recordar_gusto(
    memoria: dict[str, Any],
    config: dict[str, Any]
) -> None:
    gusto = obtener_ultimo_gusto(memoria)

    if gusto:
        responder_personalidad(f"Recuerdo esto: {gusto}", config)
        return

    responder_personalidad("Todavía no sé tus gustos", config)


def _mostrar_historial(
    memoria: dict[str, Any],
    config: dict[str, Any]
) -> str:
    historial = memoria["historial"]

    if len(historial) == 0:
        return "No tengo historial"

    return "\n".join(f"- {entrada}" for entrada in historial[-10:])


def _guardar(guardar_func: GuardarFunc | None) -> None:
    if guardar_func:
        guardar_func()