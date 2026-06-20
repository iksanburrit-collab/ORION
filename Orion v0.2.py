import datetime  # ✔ correcto: importas librería ya incluida en Python

print("Iniciando ORION v0.1")

while True:

    comando = input("\nORION> ")

    # Convierte todo a minúsculas para evitar errores como "Hola", "HOLA", etc.
    comando = comando.lower()

    if comando == "hola":
        print("Hola, ¿en que puedo ayudarte?")

    elif comando == "estado":
        print("Sistema operativo")

    elif comando == "version":
        print("ORION v0.1")

    elif comando == "fecha":
        # ✔ Esto funciona, pero muestra fecha + hora completa
        fecha_actual = datetime.datetime.now()
        print(f"Fecha: {fecha_actual}")

    elif comando == "hora":
        # ❌ ERROR ORIGINAL TUYO:
        # estabas usando .time() que da un formato técnico poco legible
        # y a veces parece que "no funciona"
        #
        # ✔ SOLUCIÓN: usar strftime para formato bonito
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