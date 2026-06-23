import datetime
import json
import os
import math
import random

print("Iniciando ORION v1.0...")

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

def calculadora():
    print("\n🧮 Calculadora ORION")
    print("suma, resta, multi, div, pot, raiz")
    print("salir para volver")

    while True:
        op = input("CALC> ").lower()

        if op == "salir":
            break

        elif op in ["suma", "resta", "multi", "div", "pot"]:
            try:
                a = float(input("Número 1: "))
                b = float(input("Número 2: "))
            except:
                print("Número inválido")
                continue

            if op == "suma":
                print(a + b)
            elif op == "resta":
                print(a - b)
            elif op == "multi":
                print(a * b)
            elif op == "div":
                if b == 0:
                    print("No se puede dividir entre 0")
                else:
                    print(a / b)
            elif op == "pot":
                print(a ** b)

        elif op == "raiz":
            try:
                a = float(input("Número: "))
                if a < 0:
                    print("No permitido en reales")
                else:
                    print(math.sqrt(a))
            except:
                print("Número inválido")

        else:
            print("Operación no válida")

while True:

    comando = input("\nORION> ").lower().strip()

    edad = calcular_edad(fecha_nacimiento)

    if any(x in comando for x in ["hola", "hey", "buenas", "que onda", "como estas"]):

        if nombre == "":
            print(random.choice([
                "Hey 👋",
                "Qué onda 😄",
                "Aquí ando 🤖"
            ]))
        else:
            print(f"Hey {nombre} 👋")

    elif any(x in comando for x in ["hora", "que hora", "dime la hora"]):
        print(datetime.datetime.now().strftime("%H:%M:%S"))

    elif any(x in comando for x in ["fecha", "que fecha", "dia"]):
        print(datetime.datetime.now().strftime("%Y-%m-%d"))

    elif any(x in comando for x in ["estado", "como estas"]):
        print("Estoy funcionando 👍")

    elif any(x in comando for x in ["version", "que version"]):
        print("ORION v1.0")

    elif "nombre" in comando:
        nombre = input("Dime tu nombre: ").strip()
        memoria["nombre"] = nombre
        guardar_memoria()
        print("Guardado 👍")

    elif "cumple" in comando:
        fecha_nacimiento = input("Fecha (YYYY-MM-DD): ").strip()
        memoria["fecha_nacimiento"] = fecha_nacimiento
        guardar_memoria()

        edad = calcular_edad(fecha_nacimiento)
        print(f"Guardado 👍 tienes {edad} años")

    elif any(x in comando for x in [
        "edad",
        "mi edad",
        "que edad tengo",
        "cuantos años tengo"
    ]):
        if fecha_nacimiento == "":
            print("No tengo tu fecha de nacimiento 😅 usa 'cumple'")
        else:
            edad = calcular_edad(fecha_nacimiento)
            print(f"Tienes {edad} años")

    elif "perfil" in comando:

        if nombre == "" or fecha_nacimiento == "":
            print("Falta información 😅 usa nombre y cumple")
        else:
            print(f"""
📌 PERFIL
Nombre: {nombre}
Nacimiento: {fecha_nacimiento}
Edad: {edad}
""")

    elif "calc" in comando:
        calculadora()

    elif any(x in comando for x in ["ayuda", "help"]):
        print("""
Comandos disponibles:
nombre
cumple
perfil
estado
version
fecha
hora
calc
salir
""")

    # SALIR
    elif "salir" in comando:
        print("Apagando ORION 👋")
        break

    else:
        print("No entendí eso 😅 usa 'ayuda'")