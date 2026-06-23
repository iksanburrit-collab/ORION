import datetime
import json
import os
import random

print("Iniciando ORION v1.4...")

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


def guardar():
    with open("memoria.json", "w") as file:
        json.dump(memoria, file, indent=4)


def calcular_edad(fecha):

    if fecha == "":
        return ""

    try:
        nacimiento = datetime.datetime.strptime(fecha, "%Y-%m-%d")
        hoy = datetime.datetime.now()

        edad = hoy.year - nacimiento.year

        if (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day):
            edad -= 1

        return edad

    except:
        return ""

def detectar_intencion(texto):

    texto = texto.lower()

    if any(x in texto for x in ["hola", "hey", "buenas", "que onda", "saludos"]):
        return "saludo"

    elif any(x in texto for x in ["hora", "que hora", "dime la hora", "tienes hora"]):
        return "hora"

    elif any(x in texto for x in ["fecha", "que fecha", "que dia", "dia"]):
        return "fecha"

    elif any(x in texto for x in ["edad", "mi edad", "cuantos años", "que edad"]):
        return "edad"

    elif "perfil" in texto:
        return "perfil"

    elif "nombre" in texto:
        return "nombre"

    elif "cumple" in texto:
        return "cumple"

    elif any(x in texto for x in ["estado", "como estas"]):
        return "estado"

    elif "calc" in texto or "+" in texto or "-" in texto or "*" in texto or "/" in texto or "raiz" in texto or "pot" in texto:
        return "calc"

    elif "version" in texto:
        return "version"

    elif "ayuda" in texto:
        return "ayuda"

    elif "salir" in texto:
        return "salir"

    return "desconocido"



while True:

    comando = input("\nORION> ").strip()

    intencion = detectar_intencion(comando)

    edad = calcular_edad(fecha_nacimiento)

    if intencion == "saludo":

        print(random.choice([
            f"Hey {nombre} 👋" if nombre else "Hey 👋",
            "Qué onda 😄",
            "Aquí ando 🤖"
        ]))

    elif intencion == "hora":

        print(datetime.datetime.now().strftime("%H:%M:%S"))

    elif intencion == "fecha":

        print(datetime.datetime.now().strftime("%Y-%m-%d"))

    elif intencion == "edad":

        if fecha_nacimiento == "":
            print("No tengo tu fecha 😅 usa cumple")
        else:
            print(f"Tienes {edad} años")

    elif intencion == "nombre":

        nombre = input("Cómo te llamas: ").strip()
        memoria["nombre"] = nombre
        guardar()

        print("Guardado 👍")

    elif intencion == "cumple":

        fecha_nacimiento = input("YYYY-MM-DD: ").strip()
        memoria["fecha_nacimiento"] = fecha_nacimiento
        guardar()

        print("Guardado 👍")

    elif intencion == "perfil":

        print(f"""
Nombre: {nombre}
Nacimiento: {fecha_nacimiento}
Edad: {edad}
""")

    elif intencion == "estado":

        print(random.choice([
            "Todo bien 👍",
            "Funcionando 😄",
            "Listo para ayudar 🤖"
        ]))

    elif intencion == "calc":

        texto = comando.lower().strip()

        if texto == "calc":

            print("""
Calculadora ORION

Ejemplos:

5+5
20/2
2^10
raiz 81
pot 2 8
""")

        else:

            try:

                if texto.startswith("raiz"):

                    numero = float(texto.replace("raiz", "").strip())

                    if numero < 0:
                        print("No permitido en reales 😅")
                    else:
                        print(f"🧮 {numero**0.5}")

                elif texto.startswith("pot"):

                    partes = texto.split()
                    base = float(partes[1])
                    exponente = float(partes[2])

                    print(f"🧮 {base**exponente}")

                else:

                    texto = texto.replace("^", "**")

                    if "/0" in texto:
                        print("No se puede dividir entre 0 😅")
                    else:
                        resultado = eval(texto)
                        print(f"🧮 {resultado}")

            except:
                print("Operación inválida 😅")

    elif intencion == "version":
        print("ORION v1.4")

    elif intencion == "ayuda":

        print("""
Comandos:

hola
nombre
cumple
edad
perfil
hora
fecha
estado
calc
version
salir
""")

    elif intencion == "salir":
        print("Apagando ORION 👋")
        break

    else:
        print(random.choice([
            "No entendí 😅",
            "Explícame diferente 🤔",
            "Intenta otra frase 👀"
        ]))