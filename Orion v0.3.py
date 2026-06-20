import datetime  

print("Iniciando ORION v0.3...")

nombre = ""

while True:

    comando = input("\nORION> ")
    comando = comando.lower()

    if comando == "hola":
        if nombre != "":
            print(f"Hola {nombre}, ¿en qué puedo ayudarte?")
        else:
            print("Hola, ¿en qué puedo ayudarte?")

    elif comando == "estado":
        print("Sistema operativo")

    elif comando == "version":
        print("ORION v0.3")

    elif comando == "fecha":
        fecha_actual = datetime.datetime.now()
        print(f"Fecha: {fecha_actual}")

    elif comando == "hora":
        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
        print("Hora:", hora_actual)

    elif comando == "nombre":
        nombre = input("¿Cómo te llamas? ")
        print(f"OK {nombre}, lo recordaré")

    elif comando == "ayuda":
        print("""
Comandos disponibles:
hola
nombre
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