import datetime
import json
import os
import math

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

saludos = [
    "hola",
    "buenas",
    "hey",
    "que onda",
]

hora_cmd = [
    "hora",
    "que hora",
    "dime la hora"
]

fecha_cmd = [
    "fecha",
    "que fecha",
    "dia"
]
ayuda_cmd = [
    "ayuda",
    "help",
]
estado_cmd = [
    "estado",
    "como estas",
]
version_cmd = [
    "version",
    "que version",
]

while True:

    comando = input("\nORION> ").lower()

    edad = calcular_edad(fecha_nacimiento)

    if any(p in comando for p in saludos):

        if nombre == "":
            print("Hey 👋 ¿en qué te ayudo?")
        else:
            print(f"Hey {nombre} 👋")

    elif any(p in comando for p in hora_cmd):
        print(datetime.datetime.now().strftime("%H:%M:%S"))

    elif any(p in comando for p in fecha_cmd):
        print(datetime.datetime.now().strftime("%Y-%m-%d"))

    elif any(p in comando for p in estado_cmd):
        print("Estoy funcionando 👍")

    elif any(p in comando for p in version_cmd):
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

    elif any(p in comando for p in ayuda_cmd):
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

    elif "salir" in comando:
        print("Apagando ORION 👋")
        break

    else:
        print("Hmm 🤔 no entendí eso")