"""
Módulo de interpretación de intenciones.

Responsabilidades:

- Analizar el mensaje del usuario.
- Detectar qué acción quiere realizar.
- Devolver una intención para que main.py actúe.
"""

def detectar_intencion(t):

    t = t.lower()
    t = " ".join(t.split())

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

    if t in {
        "hora",
        "que hora es",
        "qué hora es",
        "dime la hora",
        "hora actual",
    }:
        return "hora"

    if t in {
        "fecha",
        "que fecha es",
        "qué fecha es",
        "que dia es hoy",
        "qué dia es hoy",
        "que día es hoy",
        "qué día es hoy",
        "dime la fecha",
        "fecha actual",
        "en que fecha estamos",
        "en qué fecha estamos",
    }:
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

    if "ayuda" in t:
        return "ayuda"

    if "salir" in t:
        return "salir"

    return "desconocido"
