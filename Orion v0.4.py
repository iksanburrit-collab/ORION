import datetime

print("Iniciando ORION v0.4...")

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
        print("ORION v0.4")

    elif comando == "fecha":

        # ✔ Funciona
        fecha_actual = datetime.datetime.now()

        print(f"Fecha: {fecha_actual}")

    elif comando == "hora":

        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")

        print("Hora:", hora_actual)

    elif comando == "nombre":

        nombre = input("¿Cómo te llamas? ")

        print(f"OK {nombre}, lo recordaré")

    elif comando == "edad":

        edad = input("¿Cuántos años tienes? ")

        print(f"OK {edad}, lo recordaré")

    elif comando == "perfil":

        if nombre == "" or edad == "":

            print("""
Perfil incompleto.
Configura nombre y edad.
""")

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