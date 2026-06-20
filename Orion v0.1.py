print("Iniciando ORION v0.1")

while True:

    comando = input("\nORION> ")

    # OPCIONAL: .lower() para aceptar Hola, HOLA, hola
    comando = comando.lower()

    if comando == "hola":
        print("Hola, ¿en que puedo ayudarte?")

    elif comando == "estado":
        print("Sistema operativo")
        
    elif comando == "version":
        print("ORION v0.1")


    elif comando == "ayuda":
        print("""
hola
estado
salir
 version
""")
    elif comando == "salir":
        print("Saliendo de ORION...")
        break

    else:
        print("Comando desconocido")