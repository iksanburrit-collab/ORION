"""
Módulo de interpretación de intenciones.

Responsabilidades:

- Analizar el mensaje del usuario.
- Detectar qué acción quiere realizar.
- Devolver una intención para que main.py actúe.

Las coincidencias usan límites de palabra o frases completas para evitar
falsos positivos por subcadenas ("they" no saluda, "estados unidos" no es
estado, "123-456-7890" no es un cálculo).
"""

import re


_SIMBOLOS_CALCULADORA = re.compile(r"[0-9.\s+\-*/^()]+")

_SALUDO = re.compile(r"\b(hol+a+|hey|buenas)\b")
_NOMBRE = re.compile(r"\bnombre\b")
_CUMPLE = re.compile(r"\bcumples?\b")
_PERFIL = re.compile(r"\bperfil\b")
_EDAD = re.compile(r"\bedad\b")
_ESTADO = re.compile(r"\bestado\b")
_AYUDA = re.compile(r"\b(ayuda|ayudame|ayúdame)\b")
_SALIR = re.compile(r"\bsalir\b")
_NEGACION = re.compile(r"^(?:no|nunca|tampoco)\b")

_ENLACE_O_RUTA = re.compile(
    r"^(?:"
    r"[a-z][a-z0-9+.\-]*://\S+"       # URL con esquema (https://...)
    r"|www\.\S+"                      # URL www
    r"|/.*"                           # ruta absoluta
    r"|~/.*"                          # ruta con ~
    r"|\.\.?/\S+"                     # ruta relativa
    r"|[a-z]:[\\/].*"                 # ruta de Windows (C:/...)
    r"|[^\s@]+@[^\s@]+\.[^\s@]+"      # correo
    r")$"
)

_HORA = frozenset({
    "hora",
    "que hora es",
    "qué hora es",
    "dime la hora",
    "hora actual",
})

_FECHA = frozenset({
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
})


def _es_calculo(texto: str) -> bool:
    if texto.startswith("raiz "):
        return True
    if re.fullmatch(r"pot\s+\S+\s+\S+", texto):
        return True
    if texto.startswith("sqrt("):
        return True
    if not _SIMBOLOS_CALCULADORA.fullmatch(texto):
        return False
    if not any(operador in texto for operador in ("+", "-", "*", "/", "^")):
        return False

    # Cadenas de dígitos sin espacios, paréntesis, potencia ni decimales
    # (teléfonos, fechas o rangos como "123-456-7890" o "15/08/2026")
    # no se interpretan como cálculos.
    if not any(marcador in texto for marcador in (" ", "(", ")", "^", ".")):
        operandos = re.findall(r"\d+", texto)
        if operandos and all(len(operando) >= 2 for operando in operandos):
            return False

    return True


def detectar_intencion(t):

    t = t.lower()
    t = " ".join(t.split())

    if _ENLACE_O_RUTA.match(t):
        return "desconocido"

    if _SALUDO.search(t):
        return "saludo"

    if _NOMBRE.search(t):
        return "nombre"

    if _CUMPLE.search(t):
        return "cumple"

    if _PERFIL.search(t):
        return "perfil"

    if _EDAD.search(t):
        return "edad"

    if t in _HORA:
        return "hora"

    if t in _FECHA:
        return "fecha"

    if _ESTADO.search(t):
        return "estado"

    if _es_calculo(t):
        return "calc"

    if _AYUDA.search(t):
        return "ayuda"

    if _SALIR.search(t) and not _NEGACION.match(t):
        return "salir"

    return "desconocido"