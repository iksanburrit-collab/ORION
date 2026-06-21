import datetime
import json
import os

print("Iniciando ORION v0.8...")
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
def guardar_memoria():
    with open("memoria.json", "w") as file:
        json.dump(memoria, file)
while True:

    comando = input("\nORION> ").lower()
    if comando == "hola":

        edad = calcular_edad(fecha_nacimiento)

        if nombre == "":
            print("Hey 👋 ¿en qué puedo ayudarte hoy?")

        elif edad == "":
            print(f"Hey {nombre} 👋 ¿qué necesitas?")

        else:
            print(f"Hey {nombre} 👋 , ¿qué quieres hacer hoy?")
    elif comando == "estado":
        print("Estoy funcionando bien 👍")

    elif comando == "version":
        print("ORION v0.8")

    elif comando == "fecha":
        print("Hoy es:", datetime.datetime.now().strftime("%Y-%m-%d"))

    elif comando == "hora":
        print("Son las:", datetime.datetime.now().strftime("%H:%M:%S"))
    elif comando == "nombre":
        nombre = input("Dime tu nombre: ").strip()

        print(f"Perfecto {nombre} 👍 lo voy a recordar")

        memoria["nombre"] = nombre
        guardar_memoria()
    elif comando == "cumple":
        fecha_nacimiento = input("Tu fecha de nacimiento (YYYY-MM-DD): ").strip()

        edad = calcular_edad(fecha_nacimiento)

        print(f"Listo 👍 ya lo guardé. Tienes {edad} años")

        memoria["fecha_nacimiento"] = fecha_nacimiento
        guardar_memoria()
    elif comando == "perfil":

        edad = calcular_edad(fecha_nacimiento)

        if nombre == "" or fecha_nacimiento == "":
            print("Aún no tengo tu perfil completo 😅 usa nombre y cumple")
        else:
            print(f"""
📌 Tu perfil:
👤 Nombre: {nombre}
🎂 Nacimiento: {fecha_nacimiento}
🎯 Edad: {edad}
""")
    elif comando == "ayuda":
        print("""
Puedes usar:
- hola
- nombre
- cumple
- perfil
- estado
- version
- fecha
- hora
- salir
""")
    elif comando == "salir":
        print("Nos vemos 👋 apagando ORION...")
        break
    else:
        print("Hmm 🤔 no entendí eso, intenta con 'ayuda'")