import datetime
import json
import os
import math
import random

print("Iniciando ORION v1.3...")


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

while True:

    comando = input("\nORION> ").lower().strip()

    edad = calcular_edad(fecha_nacimiento)

    if any(x in comando for x in ["hola", "hey", "buenas", "que onda"]):

        print(random.choice([
            f"Hey {nombre} 👋" if nombre else "Hey 👋",
            "Qué onda 😄",
            "Aquí ando 🤖"
        ]))

    elif any(x in comando for x in ["hora", "que hora", "dime la hora"]):
        print(datetime.datetime.now().strftime("%H:%M:%S"))

    elif any(x in comando for x in ["fecha", "que fecha", "dia"]):
        print(datetime.datetime.now().strftime("%Y-%m-%d"))

    elif any(x in comando for x in ["estado", "como estas"]):
        print(random.choice([
            "Todo bien 👍",
            "Funcionando sin problemas 🤖",
            "Aquí ando listo 😄"
        ]))

    elif "version" in comando:
        print("ORION v1.3")

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
📌 PERFIL
Nombre: {nombre}
Nacimiento: {fecha_nacimiento}
Edad: {edad}
""")

    elif any(op in comando for op in ["+", "-", "*", "/", "**"]):

        try:
            resultado = eval(comando)
            print(resultado)
        except:
            print("No entendí la operación 🤔")

    elif "ayuda" in comando:
        print("""
Comandos:
nombre
cumple
perfil
estado
version
hora
fecha
calc (usa operaciones directas)
salir
""")

    elif "salir" in comando:
        print("Apagando ORION 👋")
        break


    else:
        print("No entendí eso 😅")