import datetime

print("Iniciando ORION v0.5...")

# 🧠 Cargar memoria correctamente
try:
    with open("memoria.txt", "r") as file:
        datos = file.read().splitlines()

    nombre = datos[0] if len(datos) > 0 else ""
    edad = datos[1] if len(datos) > 1 else ""

except:
    nombre = ""
    edad = ""

while True:

    comando = input("\nORION> ")
    comando = comando.lower()

    if comando == "hola":

        if nombre == "":
            print("Hola, ¿en qué puedo ayudarte?")

        elif edad == "":
            print(f"Hola {nombre}, ¿en qué puedo ayudarte?")

        else:
            print(f"Hola {nombre} ({edad}), ¿en qué puedo ayudarte?")

    elif comando == "estado":
        print("Sistema operativo")

    elif comando == "version":
        print("ORION v0.5")

    elif comando == "fecha":
        fecha_actual = datetime.datetime.now()
        print("Fecha:", fecha_actual)

    elif comando == "hora":
        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
        print("Hora:", hora_actual)

    elif comando == "nombre":
        nombre = input("¿Cómo te llamas? ")
        print(f"OK {nombre}, lo recordaré")

        with open("memoria.txt", "w") as file:
            file.write(nombre + "\n" + edad)

    elif comando == "edad":
        edad = input("¿Cuántos años tienes? ")
        print(f"OK {edad}, lo recordaré")

        with open("memoria.txt", "w") as file:
            file.write(nombre + "\n" + edad)

    elif comando == "perfil":

        if nombre.strip() == "" or edad.strip() == "":
            print("Perfil incompleto. Configura nombre y edad.")
        else:
            print(f"""
Perfil:
Nombre: {nombre}
Edad: {edad}
""")

    elif comando == "ayuda":
        print("""
Comandos disponibles:
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