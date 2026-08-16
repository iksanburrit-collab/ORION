"""
Módulo de interpretación de intenciones.

Responsabilidades:

- Analizar el mensaje del usuario.
- Detectar qué acción quiere realizar.
- Devolver una intención para que main.py actúe.
"""

import re


_EXPRESION_CALCULADORA = re.compile(r"[0-9.\s+\-*/^()]+")


def _es_calculo(texto: str) -> bool:
    if texto.startswith("raiz "):
        return True
    if re.fullmatch(r"pot\s+\S+\s+\S+", texto):
        return True
    if texto.startswith("sqrt("):
        return True
    return bool(_EXPRESION_CALCULADORA.fullmatch(texto)) and any(
        operador in texto for operador in ("+", "-", "*", "/", "^")
    )

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

    if _es_calculo(t):
        return "calc"

    if "ayuda" in t:
        return "ayuda"

    if "salir" in t:
        return "salir"

    return "desconocido"
