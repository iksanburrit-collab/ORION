import datetime
import json
import os
import math
import random

print("Iniciando ORION v1.2...")

if os.path.exists("memoria.json"):
    try:
        with open("memoria.json", "r") as file:
            memoria = json.load(file)
    except:
        memoria = {}
else:
    memoria = {}

nombre = memoria.get("nombre", "")
fecha_nacimiento = memoria.get("fecha_nacimiento", "")
ultima_accion = ""

def calcular_edad(fecha_str):
    try:
        if not fecha_str:
            return ""

        fecha = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
        hoy = datetime.datetime.now()

        edad = hoy.year - fecha.year

        if (hoy.month, hoy.day) < (fecha.month, fecha.day):
            edad -= 1

        return edad
    except:
        return ""

def guardar_memoria():
    with open("memoria.json", "w") as file:
        json.dump(memoria, file, indent=4)

def responder_hora():
    return datetime.datetime.now().strftime("%H:%M:%S")

def responder_fecha():
    return datetime.datetime.now().strftime("%Y-%m-%d")

while True:

    comando = input("\nORION> ").lower().strip()

    edad = calcular_edad(fecha_nacimiento)

    if any(x in comando for x in ["hola", "hey", "buenas", "que onda"]):

        ultima_accion = "saludo"

        if nombre == "":
            print(random.choice(["Hey 👋", "Qué onda 😄", "Aquí ando 🤖"]))
        else:
            print(f"Hey {nombre} 👋")

    elif any(x in comando for x in ["hora"]):

        ultima_accion = "hora"
        print(responder_hora())

    elif any(x in comando for x in ["fecha"]):

        ultima_accion = "fecha"
        print(responder_fecha())

    elif any(x in comando for x in ["estado", "como estas"]):

        ultima_accion = "estado"
        print("Todo bien 👍")

    elif "version" in comando:
        print("ORION v1.2")

    elif "nombre" in comando:
        nombre = input("Dime tu nombre: ").strip()
        memoria["nombre"] = nombre
        guardar_memoria()
        print("Guardado 👍")

    elif "cumple" in comando:
        fecha_nacimiento = input("Fecha (YYYY-MM-DD): ").strip()
        memoria["fecha_nacimiento"] = fecha_nacimiento
        guardar_memoria()

        print(f"Guardado 👍 tienes {calcular_edad(fecha_nacimiento)} años")

    elif any(x in comando for x in ["edad", "mi edad", "cuantos años tengo"]):

        if fecha_nacimiento == "":
            print("No tengo tu fecha 😅 usa 'cumple'")
        else:
            print(f"Tienes {edad} años")

    elif "perfil" in comando:

        if nombre == "" or fecha_nacimiento == "":
            print("Falta información 😅")
        else:
            print(f"""
Nombre: {nombre}
Nacimiento: {fecha_nacimiento}
Edad: {edad}
""")

    elif "repite" in comando:

        if ultima_accion == "hora":
            print(responder_hora())
        elif ultima_accion == "fecha":
            print(responder_fecha())
        elif ultima_accion == "saludo":
            print(f"Hey {nombre} 👋" if nombre else "Hey 👋")
        else:
            print("No tengo nada que repetir 🤔")

    elif "calc" in comando:
        print("Calculadora aún básica en v1.2")

    elif "ayuda" in comando:
        print("""
nombre
cumple
perfil
estado
version
fecha
hora
repite
calc
salir
""")

    elif "salir" in comando:
        print("Apagando ORION 👋")
        break

    else:
        print("No entendí eso 😅")