import datetime 

print("Iniciando ORION v0.1")

while True:

    comando = input("\nORION> ")

  
    comando = comando.lower()

    if comando == "hola":
        print("Hola, ¿en que puedo ayudarte?")

    elif comando == "estado":
        print("Sistema operativo")

    elif comando == "version":
        print("ORION v0.1")

    elif comando == "fecha":
        fecha_actual = datetime.datetime.now()
        print(f"Fecha: {fecha_actual}")

    elif comando == "hora":
        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
        print("Hora:", hora_actual)

    elif comando == "ayuda":
        print("""
Comandos disponibles:
hola
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
