import datetime
import json
import os

print("Iniciando ORION v0.7...")

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
        fecha_nac = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
        hoy = datetime.datetime.now()

        edad = hoy.year - fecha_nac.year

        if (hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day):
            edad -= 1

        return edad
    except:
        return ""

while True:

    comando = input("\nORION> ").lower()

    if comando == "hola":

        edad = calcular_edad(fecha_nacimiento)

        if nombre == "":
            print("Hola, ¿en qué puedo ayudarte?")

        elif edad == "":
            print(f"Hola {nombre}, ¿en qué puedo ayudarte?")

        else:
            print(f"Hola {nombre}, ¿en qué puedo ayudarte?")

    elif comando == "estado":
        print("Sistema operativo")

    elif comando == "version":
        print("ORION v0.7")

    elif comando == "fecha":
        print("Fecha:", datetime.datetime.now())

    elif comando == "hora":
        print("Hora:", datetime.datetime.now().strftime("%H:%M:%S"))

    elif comando == "nombre":
        nombre = input("¿Cómo te llamas? ")
        print(f"OK {nombre}, lo recordaré")

        memoria["nombre"] = nombre

        with open("memoria.json", "w") as file:
            json.dump(memoria, file)

    elif comando == "cumple":
        fecha_nacimiento = input("Fecha de nacimiento (YYYY-MM-DD): ")
        print("OK, lo recordaré")

        memoria["nombre"] = nombre
        memoria["fecha_nacimiento"] = fecha_nacimiento

        with open("memoria.json", "w") as file:
            json.dump(memoria, file)

    elif comando == "perfil":

        edad = calcular_edad(fecha_nacimiento)

        if nombre == "" or fecha_nacimiento == "":
            print("Perfil incompleto. Configura nombre y fecha de nacimiento.")
        else:
            print(f"""
Perfil:
Nombre: {nombre}
Fecha de nacimiento: {fecha_nacimiento}
Edad: {edad}
""")

    elif comando == "ayuda":
        print("""
Comandos:
hola
nombre
perfil
cumple (guardar fecha de nacimiento)
estado
version
fecha
hora
salir
""")

    elif comando == "salir":
        print("Saliendo de ORION...")
        break

    else:
        print("Comando desconocido")