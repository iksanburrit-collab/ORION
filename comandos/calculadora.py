def ejecutar_calculadora(comando):

    try:

        t = comando

        if "raiz" in t:

            n = float(
                t.replace(
                    "raiz",
                    ""
                )
            )

            if n < 0:

                print(
                    "No permitido 😅"
                )

            else:

                print(
                    f"🧮 {n**0.5}"
                )

        elif "pot" in t:

            p = t.split()

            print(
                f"🧮 {float(p[1])**float(p[2])}"
            )

        else:

            t = t.replace(
                "^",
                "**"
            )

            if "/0" in t:

                print(
                    "No se puede dividir entre 0 😅"
                )

            else:

                print(
                    f"🧮 {eval(t)}"
                )

    except:

        print(
            "Operación inválida 😅"
        )
