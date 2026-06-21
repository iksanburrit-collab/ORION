import datetime
import json
import os
import math

print("Iniciando ORION v0.9...")
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

        fecha_nac = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
        hoy = datetime.datetime.now()

        edad = hoy.year - fecha_nac.year

        if (hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day):
            edad -= 1

        return edad
    except:
        return ""

def guardar_memoria():
    with open("memoria.json", "w") as file:
        json.dump(memoria, file)

def calculadora():
    print("\n🧮 Calculadora ORION")
    print("suma, resta, multi, div, pot, raiz")
    print("escribe salir para volver")

    while True:
        op = input("CALC> ").lower()

        if op == "salir":
            break

        elif op in ["suma", "resta", "multi", "div", "pot"]:
            a = float(input("Número 1: "))
            b = float(input("Número 2: "))

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
            a = float(input("Número: "))
            if a < 0:
                print("No permitido en reales")
            else:
                print(math.sqrt(a))

        else:
            print("Operación no válida")
while True:

    comando = input("\nORION> ").lower()

    edad = calcular_edad(fecha_nacimiento)

    if comando == "hola":

        if nombre == "":
            print("Hey 👋 ¿en qué te ayudo?")
        else:
            print(f"Hey {nombre} 👋")

    elif comando == "estado":
        print("Estoy funcionando 👍")

    elif comando == "version":
        print("ORION v0.9")

    elif comando == "fecha":
        print(datetime.datetime.now().strftime("%Y-%m-%d"))

    elif comando == "hora":
        print(datetime.datetime.now().strftime("%H:%M:%S"))

    elif comando == "nombre":
        nombre = input("Dime tu nombre: ").strip()
        memoria["nombre"] = nombre
        guardar_memoria()
        print("Guardado 👍")

    elif comando == "cumple":
        fecha_nacimiento = input("Fecha (YYYY-MM-DD): ").strip()
        memoria["fecha_nacimiento"] = fecha_nacimiento
        guardar_memoria()

        edad = calcular_edad(fecha_nacimiento)
        print(f"Guardado 👍 tienes {edad} años")

    elif comando == "perfil":

        if nombre == "" or fecha_nacimiento == "":
            print("Falta información 😅 usa nombre y cumple")
        else:
            print(f"""
📌 PERFIL
Nombre: {nombre}
Nacimiento: {fecha_nacimiento}
Edad: {edad}
""")

    elif comando == "ayuda":
        print("""
Comandos disponibles:
hola
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

    elif comando == "calc":
        calculadora()

    elif comando == "salir":
        print("Apagando ORION 👋")
        break

    else:
        print("Hmm 🤔 no entendí eso")