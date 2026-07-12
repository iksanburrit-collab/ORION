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
                return "No permitido 😅"

            return f"🧮 {n**0.5}"

        if "pot" in t:
            p = t.split()
            return f"🧮 {float(p[1])**float(p[2])}"

        t = t.replace(
            "^",
            "**"
        )

        if "/0" in t:
            return "No se puede dividir entre 0 😅"

        return f"🧮 {eval(t)}"

    except Exception:
        return "Operación inválida 😅"
