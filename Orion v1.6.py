import datetime
import json
import os
import random
import urllib.parse

print("Iniciando ORION v1.6 (Navegador Pro)...")

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

nombre = memoria["nombre"]
fecha_nacimiento = memoria["fecha_nacimiento"]


def guardar():
    with open("memoria.json", "w") as file:
        json.dump(memoria, file, indent=4)



def navegador_inteligente(texto):

    t = texto.lower().strip()

    if "google" in t or t.startswith("busca") or t.startswith("buscar"):

        query = t.replace("google", "").replace("busca", "").replace("buscar", "").strip()
        if query == "":
            query = "google"

        url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
        os.startfile(url)
        return True

    if "youtube" in t or "yt" in t:

        query = t.replace("youtube", "").replace("yt", "").replace("busca", "").strip()

        if query == "":
            url = "https://www.youtube.com"
        else:
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)

        os.startfile(url)
        return True

    if "chatgpt" in t or "openai" in t or "ia" in t:

        os.startfile("https://chat.openai.com")
        return True

    if "abre google" in t:
        os.startfile("https://www.google.com")
        return True

    if "abre youtube" in t:
        os.startfile("https://www.youtube.com")
        return True

    if "gmail" in t:
        os.startfile("https://mail.google.com")
        return True

    return False

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

while True:

    comando = input("\nORION> ").strip().lower()

    # guardar historial
    memoria["historial"].append(comando)
    if len(memoria["historial"]) > 10:
        memoria["historial"].pop(0)

    guardar()

    if navegador_inteligente(comando):
        continue

    edad = calcular_edad(fecha_nacimiento)

    if any(x in comando for x in ["hola", "hey", "buenas", "que onda"]):
        print(random.choice([
            f"Hey {nombre} 👋" if nombre else "Hey 👋",
            "Qué onda 😄",
            "Aquí ando 🤖"
        ]))

    elif "hora" in comando:
        print(datetime.datetime.now().strftime("%H:%M:%S"))

    elif "fecha" in comando or "dia" in comando:
        print(datetime.datetime.now().strftime("%Y-%m-%d"))

    elif "edad" in comando:
        print(f"Tienes {edad} años" if fecha_nacimiento else "No tengo tu fecha 😅 usa cumple")

    elif "nombre" in comando:
        nombre = input("Cómo te llamas: ").strip()
        memoria["nombre"] = nombre
        guardar()
        print("Guardado 👍")

    elif "cumple" in comando:
        fecha_nacimiento = input("YYYY-MM-DD: ").strip()
        memoria["fecha_nacimiento"] = fecha_nacimiento
        guardar()
        print("Guardado 👍")

    elif "perfil" in comando:
        print(f"""
Nombre: {nombre}
Nacimiento: {fecha_nacimiento}
Edad: {edad}
""")

    elif "estado" in comando:
        print(random.choice([
            "Todo bien 👍",
            "Funcionando 😄",
            "Listo para ayudar 🤖"
        ]))

    elif "version" in comando:
        print("ORION v1.6 Navegador Pro")
  
    elif "ayuda" in comando:
        print("""
Comandos inteligentes:

🌐 Google:
- busca python
- google inteligencia artificial

▶ YouTube:
- youtube musica
- yt gameplays

🤖 IA:
- chatgpt
- ia

📌 Sistema:
- hora
- fecha
- nombre
- cumple
- perfil
- salir
""")
    elif "salir" in comando:
        print("Apagando ORION 👋")
        break
    else:
        print(random.choice([
            "No entendí 😅",
            "Intenta algo como 'busca python'",
            "Explícame diferente 🤔"
        ]))