import datetime
import json
import os
import random
import urllib.parse

print("Iniciando ORION v1.7...")

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
memoria.setdefault("historial", [])
memoria.setdefault("frases_importantes", [])

nombre = memoria["nombre"]
fecha_nacimiento = memoria["fecha_nacimiento"]


def guardar():
    with open("memoria.json", "w") as file:
        json.dump(memoria, file, indent=4)


def aprender(texto):
    t = texto.lower()
    if "me gusta" in t:
        memoria["frases_importantes"].append(t)
        guardar()


def responder_memoria(texto):
    t = texto.lower()

    if "que me gusta" in t:
        if len(memoria["frases_importantes"]) == 0:
            print("Aún no sé eso de ti 🤔")
        else:
            for x in memoria["frases_importantes"]:
                print("-", x)
        return True

    return False


def navegador_inteligente(texto):

    t = texto.lower().strip()

    if t == "youtube":
        os.startfile("https://www.youtube.com")
        return True

    if t.startswith("youtube "):
        q = t.replace("youtube ", "").strip()
        os.startfile("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
        return True

    if t.startswith("busca "):
        q = t.replace("busca ", "").strip()
        os.startfile("https://www.google.com/search?q=" + urllib.parse.quote(q))
        return True

    if t == "chatgpt":
        os.startfile("https://chat.openai.com")
        return True

    if t in ["chrome", "abrir chrome"]:
        os.system("start chrome")
        return True

    if t in ["yt music", "youtube music"]:
        os.startfile("https://music.youtube.com")
        return True

    return False


def calcular_edad(fecha):

    if not fecha:
        return ""

    try:
        n = datetime.datetime.strptime(fecha, "%Y-%m-%d")
        h = datetime.datetime.now()

        edad = h.year - n.year
        if (h.month, h.day) < (n.month, n.day):
            edad -= 1
        return edad
    except:
        return ""


def detectar_intencion(t):

    t = t.strip().lower()

    if any(x in t for x in ["hola", "hey", "buenas", "que onda"]):
        return "saludo"

    if "ayuda" in t:
        return "ayuda"

    if "version" in t:
        return "version"

    if "salir" in t:
        return "salir"

    if "nombre" in t:
        return "nombre"

    if "cumple" in t or "nacimiento" in t:
        return "cumple"

    if "perfil" in t:
        return "perfil"

    if "edad" in t:
        return "edad"

    if "hora" in t:
        return "hora"

    if "fecha" in t or "dia" in t:
        return "fecha"

    if "estado" in t:
        return "estado"

    if any(x in t for x in ["calc", "+", "-", "*", "/", "raiz", "pot"]):
        return "calc"

    if t in ["chrome", "abrir chrome"]:
        return "chrome"

    if t in ["yt music", "youtube music"]:
        return "yt_music"

    return "desconocido"


while True:

    comando = input("\nORION> ").strip().lower()

    aprender(comando)

    memoria["historial"].append(comando)
    if len(memoria["historial"]) > 10:
        memoria["historial"].pop(0)

    guardar()

    if navegador_inteligente(comando):
        continue

    if responder_memoria(comando):
        continue

    intencion = detectar_intencion(comando)
    edad = calcular_edad(fecha_nacimiento)

    if intencion == "saludo":
        print(f"Hola {nombre} 👋" if nombre else "Hola 👋")

    elif intencion == "ayuda":
        comandos = [
            "hola",
            "nombre",
            "cumple",
            "perfil",
            "edad",
            "hora",
            "fecha",
            "estado",
            "calc",
            "youtube",
            "busca",
            "chatgpt",
            "chrome",
            "yt music",
            "salir"
        ]
        print("Comandos disponibles:")
        for c in comandos:
            print("-", c)

    elif intencion == "version":
        print("ORION v1.7")

    elif intencion == "nombre":
        nombre = input("Tu nombre: ").strip()
        memoria["nombre"] = nombre
        guardar()
        print("Perfecto 👍 lo recordaré")

    elif intencion == "cumple":
        fecha_nacimiento = input("YYYY-MM-DD: ").strip()
        memoria["fecha_nacimiento"] = fecha_nacimiento
        guardar()
        print("Listo 👍 lo recordaré")

    elif intencion == "perfil":
        print(f"Nombre: {nombre}")
        print(f"Nacimiento: {fecha_nacimiento}")
        print(f"Edad: {edad}")

    elif intencion == "edad":
        print(f"Tienes {edad} años" if fecha_nacimiento else "No tengo tu fecha 😅")

    elif intencion == "hora":
        print(datetime.datetime.now().strftime("%H:%M:%S"))

    elif intencion == "fecha":
        print(datetime.datetime.now().strftime("%Y-%m-%d"))

    elif intencion == "estado":
        print(random.choice(["Todo bien 👍", "Funcionando 🤖", "Listo"]))

    elif intencion == "chrome":
        os.system("start chrome")

    elif intencion == "yt_music":
        os.startfile("https://music.youtube.com")

    elif intencion == "calc":
        try:
            texto = comando.replace("^", "**")

            if "raiz" in texto:
                n = float(texto.replace("raiz", "").strip())
                print("No permitido 😅" if n < 0 else f"🧮 {n**0.5}")

            elif "pot" in texto:
                p = texto.split()
                print(f"🧮 {float(p[1]) ** float(p[2])}")

            else:
                print(f"🧮 {eval(texto)}")

        except:
            print("Error 😅")

    elif intencion == "salir":
        print("Apagando ORION 👋")
        break

    else:
        print(random.choice(["No entendí 🤔", "Explícame diferente"]))