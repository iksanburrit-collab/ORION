import datetime
import json

print("Iniciando ORION v0.6...")
try:
    with open("memoria.json", "r") as file:
        memoria = json.load(file)
        nombre = memoria.get("nombre", "")
        edad = memoria.get("edad", "")
except:
    nombre = ""
    edad = ""

while True:

    comando = input("\nORION> ").lower()

    if comando == "hola":

        if nombre == "":
            print("Hola, ¿en qué puedo ayudarte?")
        elif edad == "":
            print(f"Hola {nombre}, ¿en qué puedo ayudarte?")
        else:
            print(f"Hola {nombre}, ¿en qué puedo ayudarte?")

    elif comando == "estado":
        print("Sistema operativo")

    elif comando == "version":
        print("ORION v0.6")

    elif comando == "fecha":
        print("Fecha:", datetime.datetime.now())

    elif comando == "hora":
        print("Hora:", datetime.datetime.now().strftime("%H:%M:%S"))

    elif comando == "nombre":
        nombre = input("¿Cómo te llamas? ")
        print(f"OK {nombre}, lo recordaré")

        with open("memoria.json", "w") as file:
            json.dump({"nombre": nombre, "edad": edad}, file)

    elif comando == "edad":
        edad = input("¿Cuántos años tienes? ")
        print(f"OK {edad}, lo recordaré")

        with open("memoria.json", "w") as file:
            json.dump({"nombre": nombre, "edad": edad}, file)

    elif comando == "perfil":

        if nombre == "" or edad == "":
            print("Perfil incompleto. Configura nombre y edad.")
        else:
            print(f"""
Perfil:
Nombre: {nombre}
Edad: {edad}
""")

    elif comando == "ayuda":
        print("""
Comandos:
hola
nombre
edad
perfil
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