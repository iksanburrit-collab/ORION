from __future__ import annotations

import random
from typing import Any

from comandos.calculadora import ejecutar_calculadora
from comandos.sistema import mostrar_ayuda, mostrar_perfil
from core.handlers.contratos import ResultadoCerebro
from core.memoria import obtener_fecha_nacimiento, obtener_nombre
from core.personalidad import responder_personalidad
from utilidades.fechas import calcular_edad, fecha_actual, hora_actual


def resolver_intencion(
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