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
    cambio = _completar_defaults(datos, defecto)

    if not os.path.exists(nombre):

        guardar_json(nombre, datos)

    elif cambio:

        guardar_json(nombre, datos)

    return datos


def _completar_defaults(datos, defecto):
    if not isinstance(datos, dict) or not isinstance(defecto, dict):
        return False

    cambio = False

    for clave, valor in defecto.items():
        if clave not in datos:
            datos[clave] = valor
            cambio = True
        elif isinstance(datos[clave], dict) and isinstance(valor, dict):
            cambio = _completar_defaults(datos[clave], valor) or cambio

    return cambio
