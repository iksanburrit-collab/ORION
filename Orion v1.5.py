import datetime
import json
import os
import random

print("Iniciando ORION v1.5...")

if os.path.exists("memoria.json"):
    try:
        with open("memoria.json", "r") as file:
            memoria = json.load(file)
    except:
        memoria = {}
else:
    memoria = {}

memoria.setdefault("nombre", "")
memoria.setdefault("fecha_nacimiento", "")
memoria.setdefault("gustos", [])
memoria.setdefault("historial", [])

nombre = memoria["nombre"]
fecha_nacimiento = memoria["fecha_nacimiento"]


def guardar():
    with open("memoria.json", "w") as file:
        json.dump(memoria, file, indent=4)


def calcular_edad(fecha):
    if not fecha:
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
    
def navegador_inteligente(texto):

    texto = texto.lower()

    if "google" in texto or "busca" in texto:

        query = texto.replace("google", "").replace("busca", "").strip()
        os.startfile(f"https://www.google.com/search?q={query}")
        return True

    if "youtube" in texto:

        query = texto.replace("youtube", "").replace("busca", "").strip()
        os.startfile(f"https://www.youtube.com/results?search_query={query}")
        return True

    if "chatgpt" in texto or "openai" in texto or "ia" in texto:

        os.startfile("https://chat.openai.com")
        return True

    if "abre google" in texto:
        os.startfile("https://www.google.com")
        return True

    if "abre youtube" in texto:
        os.startfile("https://www.youtube.com")
        return True

    return False

def detectar_intencion(texto):
    texto = texto.lower()

    if any(x in texto for x in ["hola", "hey", "buenas", "que onda", "saludos"]):
        return "saludo"

    elif any(x in texto for x in ["hora", "que hora", "dime la hora"]):
        return "hora"

    elif any(x in texto for x in ["fecha", "que dia", "dia"]):
        return "fecha"

    elif any(x in texto for x in ["edad", "cuantos años", "mi edad"]):
        return "edad"

    elif "perfil" in texto:
        return "perfil"

    elif "nombre" in texto:
        return "nombre"

    elif "cumple" in texto:
        return "cumple"

    elif any(x in texto for x in ["estado", "como estas"]):
        return "estado"

    elif (
        "calc" in texto
        or "+" in texto
        or "-" in texto
        or "*" in texto
        or "/" in texto
        or "raiz" in texto
        or "pot" in texto
    ):
        return "calc"

    elif "version" in texto:
        return "version"

    elif "ayuda" in texto:
        return "ayuda"

    elif "salir" in texto:
        return "salir"

    elif "chrome" in texto:
        return "chrome"

    elif "vscode" in texto or "visual studio" in texto:
        return "vscode"

    elif "calculadora" in texto:
        return "calc_win"

    elif "notas" in texto or "bloc" in texto:
        return "notas"
    
    elif "youtube music" in texto or "yt music" in texto:
        return "yt_music"
    
    elif "chat gpt" in texto or "openai" in texto:
        return "chatgpt"

    return "desconocido"


while True:

    comando = input("\nORION> ").strip().lower()
    if navegador_inteligente(comando):
      continue

    memoria["historial"].append(comando)
    if len(memoria["historial"]) > 10:
        memoria["historial"].pop(0)

    guardar()

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
        print(f"Tienes {edad} años" if fecha_nacimiento else "No tengo tu fecha 😅 usa cumple")

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

        texto = comando.replace("^", "**")

        if texto == "calc":
            print("""
5+5
20/2
2^10
raiz 81
pot 2 8
""")

        else:
            try:
                if texto.startswith("raiz"):
                    n = float(texto.replace("raiz", "").strip())
                    print("No permitido 😅" if n < 0 else f"🧮 {n**0.5}")

                elif texto.startswith("pot"):
                    p = texto.split()
                    print(f"🧮 {float(p[1]) ** float(p[2])}")

                else:
                    print(f"🧮 {eval(texto)}")

            except:
                print("Operación inválida 😅")

    elif intencion == "chrome":
        os.system("start chrome")

    elif intencion == "vscode":
        os.system("code")

    elif intencion == "calc_win":
        os.system("calc")

    elif intencion == "notas":
        os.system("notepad")

    elif intencion == "yt_music":
        os.startfile("https://music.youtube.com")

    elif intencion == "chatgpt":
     os.startfile("https://chat.openai.com")

    elif intencion == "version":
        print("ORION v1.5")

    elif intencion == "ayuda":
        print("""
hola
nombre
cumple
edad
perfil
hora
fecha
estado
calc
chrome
vscode
yt music
chatgpt
notas
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