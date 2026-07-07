"""
Módulo de interpretación de intenciones.

Responsabilidades:

- Analizar el mensaje del usuario.
- Detectar qué acción quiere realizar.
- Devolver una intención para que main.py actúe.
"""

def detectar_intencion(t):

    t = t.lower()

    if any(
        x in t
        for x in [
            "hola",
            "hey",
            "buenas"
        ]
    ):
        return "saludo"

    if "nombre" in t:
        return "nombre"

    if "cumple" in t:
        return "cumple"

    if "perfil" in t:
        return "perfil"

    if "edad" in t:
        return "edad"

    if "hora" in t:
        return "hora"

    if "fecha" in t:
        return "fecha"

    if "estado" in t:
        return "estado"

    if any(
        x in t
        for x in [
            "calc",
            "+",
            "-",
            "*",
            "/",
            "raiz",
            "pot",
            "^"
        ]
    ):
        return "calc"

    if "version" in t:
        return "version"

    if "ayuda" in t:
        return "ayuda"

    if "salir" in t:
        return "salir"

    return "desconocido"
