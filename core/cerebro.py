from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Callable

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


InputFunc = Callable[[str], str]
GuardarFunc = Callable[[], None]


@dataclass
class ResultadoCerebro:
    texto: str
    intencion: str
    accion: str = ""
    salir: bool = False
    conocimiento: Any | None = None

    def como_dict(self) -> dict[str, Any]:
        return {
            "texto": self.texto,
            "intencion": self.intencion,
            "accion": self.accion,
            "salir": self.salir,
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
    input_func: InputFunc = input,
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
        input_func,
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

    print(
        random.choice([
            "No entendí 🤔",
            "Explícame diferente 😄",
        ])
    )
    resultado.accion = "desconocido"
    return resultado.como_dict()


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
    input_func: InputFunc,
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
        nombre = input_func("Tu nombre: ")
        actualizar_perfil(memoria, nombre=nombre)
        guardar_memoria(memoria)
        responder_personalidad("Guardado 👍", config)
        resultado.accion = "actualizar_nombre"
        return True

    if intencion == "cumple":
        fecha_nacimiento = input_func("YYYY-MM-DD: ")
        actualizar_perfil(memoria, fecha_nacimiento=fecha_nacimiento)
        guardar_memoria(memoria)
        responder_personalidad("Guardado 👍", config)
        resultado.accion = "actualizar_cumple"
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
        print("Apagando ORION 👋")
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
    if texto.startswith("recuerda "):
        nota = texto.replace("recuerda ", "", 1)
        notas.append(nota)
        _guardar(guardar_notas)
        responder_personalidad("Nota guardada 👍", config)
        resultado.accion = "guardar_nota"
        return True

    if texto == "notas":
        if len(notas) == 0:
            responder_personalidad("No hay notas", config)
        else:
            print("\nNOTAS\n")
            for indice, nota in enumerate(notas, start=1):
                print(f"{indice}. {nota}")
        resultado.accion = "listar_notas"
        return True

    if texto == "borrar notas":
        notas.clear()
        _guardar(guardar_notas)
        responder_personalidad("Notas eliminadas", config)
        resultado.accion = "borrar_notas"
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
        _cambiar_modo(texto, config, guardar_config)
        resultado.accion = "cambiar_modo"
        return True

    if texto == "modo":
        print(f"Modo actual: {config['modo']}")
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
        _mostrar_historial(memoria, config)
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
) -> None:
    nuevo = texto.replace("modo ", "", 1)
    modos = ["normal", "ironman", "serio", "chill"]

    if nuevo in modos:
        config["modo"] = nuevo
        _guardar(guardar_config)
        responder_personalidad(f"Modo {nuevo} activado", config)
        return

    print("Modos:")
    print(modos)


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
) -> None:
    historial = memoria["historial"]

    if len(historial) == 0:
        responder_personalidad("No tengo historial", config)
        return

    print()
    for entrada in historial[-10:]:
        print("-", entrada)


def _guardar(guardar_func: GuardarFunc | None) -> None:
    if guardar_func:
        guardar_func()
