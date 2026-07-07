import random
import sys
from utilidades.archivos import asegurar_json, cargar, guardar_json
from utilidades.fechas import calcular_edad, fecha_actual, hora_actual
from utilidades.texto import normalizar_comando
from core.intenciones import detectar_intencion
from core.memoria import (
    actualizar_perfil,
    agregar_historial,
    aprender,
    guardar_contexto,
    guardar_memoria,
    inicializar_memoria,
    obtener_fecha_nacimiento,
    obtener_nombre,
    obtener_ultimo_comando,
    obtener_ultimo_gusto
)
from core.personalidad import responder_personalidad
from comandos.calculadora import ejecutar_calculadora
from comandos.navegador import navegador_inteligente
from comandos.sistema import mostrar_ayuda, mostrar_perfil


if hasattr(sys.stdout, "reconfigure"):

    sys.stdout.reconfigure(encoding="utf-8")

print("Iniciando ORION v1.8...")


memoria = inicializar_memoria(cargar("memoria.json", {}))
notas = asegurar_json("notas.json", [])
recordatorios = asegurar_json("recordatorios.json", [])
alias = asegurar_json("alias.json", {})
config = asegurar_json(
    "config.json",
    {"modo": "normal"}
)
guardar_memoria(memoria)

nombre = obtener_nombre(memoria)

fecha_nacimiento = obtener_fecha_nacimiento(memoria)


def guardar_notas():

    guardar_json("notas.json", notas)


def guardar_recordatorios():

    guardar_json("recordatorios.json", recordatorios)


def guardar_alias():

    guardar_json("alias.json", alias)


def guardar_config():

    guardar_json("config.json", config)


while True:

    comando = normalizar_comando(input(
        "\nORION> "
    ))

    aprender(comando, memoria)

    agregar_historial(
        comando,
        memoria
    )
    guardar_contexto(
        comando,
        memoria
    )

    if navegador_inteligente(
        comando
    ):
        continue

    edad = calcular_edad(
        fecha_nacimiento
    )

    intencion = detectar_intencion(
        comando
    )

    if intencion == "saludo":

        responder_personalidad(
            f"Hola {nombre} 👋"
            if nombre
            else "Hola 👋",
            config
        )

    elif intencion == "nombre":

        nombre = input(
            "Tu nombre: "
        )

        actualizar_perfil(
            memoria,
            nombre=nombre
        )

        guardar_memoria(memoria)

        responder_personalidad(
            "Guardado 👍",
            config
        )

    elif intencion == "cumple":

        fecha_nacimiento = input(
            "YYYY-MM-DD: "
        )

        actualizar_perfil(
            memoria,
            fecha_nacimiento=fecha_nacimiento
        )

        guardar_memoria(memoria)

        responder_personalidad(
            "Guardado 👍",
            config
        )

    elif intencion == "perfil":

        mostrar_perfil(nombre, edad)

    elif intencion == "edad":
        responder_personalidad(
            f"Tienes {edad} años"
            if edad
            else "No sé tu edad 😅",
            config
        )

    elif intencion == "hora":

        responder_personalidad(
            hora_actual(),
            config
        )

    elif intencion == "fecha":

        responder_personalidad(
            fecha_actual(),
            config
        )

    elif intencion == "estado":
        responder_personalidad(
            random.choice([
                "Estoy bien 😄",
                "Todo cool 😎",
                "Todo en orden 👍",
                "Procesando datos 🤖"
            ]),
            config
        )

    elif intencion == "calc":

        ejecutar_calculadora(comando)

    elif intencion == "version":

        responder_personalidad(
            "ORION v1.8",
            config
        )

    elif comando.startswith(
        "recuerda "
    ):

        nota = comando.replace(
            "recuerda ",
            ""
        )

        notas.append(
            nota
        )

        guardar_notas()

        responder_personalidad(
            "Nota guardada 👍",
            config
        )

    elif comando == "notas":

        if len(
            notas
        ) == 0:

            responder_personalidad(
                "No hay notas",
                config
            )

        else:

            print(
                "\nNOTAS\n"
            )

            for i, n in enumerate(
                notas,
                start=1
            ):

                print(
                    f"{i}. {n}"
                )

    elif comando == "borrar notas":

        notas.clear()

        guardar_notas()

        responder_personalidad(
            "Notas eliminadas",
            config
        )

    elif comando.startswith(
        "aprende:"
    ):

        try:

            texto = comando.replace(
                "aprende:",
                ""
            )

            a, b = texto.split(
                "="
            )

            alias[
                a.strip()
            ] = b.strip()

            guardar_alias()

            responder_personalidad(
                "Alias guardado 👍",
                config
            )

        except:

            responder_personalidad(
                "Formato: aprende: comando=accion",
                config
            )

    elif comando in alias:

        responder_personalidad(
            alias[comando],
            config
        )

    elif comando.startswith(
        "modo "
    ):

        nuevo = comando.replace(
            "modo ",
            ""
        )

        modos = [
            "normal",
            "ironman",
            "serio",
            "chill"
        ]

        if nuevo in modos:

            config[
                "modo"
            ] = nuevo

            guardar_config()

            responder_personalidad(
                f"Modo {nuevo} activado",
                config
            )

        else:

            print(
                "Modos:"
            )

            print(
                modos
            )

    elif comando == "modo":

        print(
            f"Modo actual: {config['modo']}"
        )

    elif "que hice" in comando:

        ultimo = obtener_ultimo_comando(memoria)

        if ultimo:

            responder_personalidad(
                f"La última orden fue: {ultimo}",
                config
            )

        else:

            responder_personalidad(
                "No recuerdo nada todavía",
                config
            )

    elif "que me gusta" in comando:

        gusto = obtener_ultimo_gusto(memoria)

        if gusto:

            responder_personalidad(
                f"Recuerdo esto: {gusto}",
                config
            )

        else:

            responder_personalidad(
                "Todavía no sé tus gustos",
                config
            )

    elif "que recuerdas" in comando:

        responder_personalidad(
            f"Tengo {len(memoria['historial'])} recuerdos recientes",
            config
        )

    elif "historial" in comando:

        if len(
            memoria[
                "historial"
            ]
        ) == 0:

            responder_personalidad(
                "No tengo historial",
                config
            )

        else:

            print()

            for x in memoria[
                "historial"
            ][-10:]:

                print(
                    "-",
                    x
                )

    elif intencion == "ayuda":
        mostrar_ayuda()

    elif intencion == "salir":

        print(
            "Apagando ORION 👋"
        )

        break
    else:

        print(
            random.choice([
                "No entendí 🤔",
                "Explícame diferente 😄"
            ])
        )
