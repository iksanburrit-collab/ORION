import json
import os


def cargar(nombre, defecto):

    if os.path.exists(nombre):

        try:

            with open(nombre, "r", encoding="utf-8") as file:

                return json.load(file)

        except:

            return defecto

    return defecto


def guardar_json(nombre, datos):

    with open(nombre, "w", encoding="utf-8") as file:

        json.dump(
            datos,
            file,
            indent=4,
            ensure_ascii=False
        )


def asegurar_json(nombre, defecto):

    datos = cargar(nombre, defecto)

    if not os.path.exists(nombre):

        guardar_json(nombre, datos)

    return datos
