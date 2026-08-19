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
    "que hora tenemos",
    "qué hora tenemos",
    "dime la hora",
    "hora actual",
    "me dices la hora",
    "dime qué hora es",
    "dime que hora es",
    "qué hora es ahora",
    "que hora es ahora",
    "qué hora tenemos ahora",
    "que hora tenemos ahora",
    "sabes qué hora es",
    "sabes que hora es",
    "cuál es la hora",
    "cual es la hora",
})

_FECHA = frozenset({
    "fecha",
    "que fecha es",
    "qué fecha es",
    "que fecha es hoy",
    "qué fecha es hoy",
    "cual es la fecha de hoy",
    "cuál es la fecha de hoy",
    "cual es la fecha",
    "cuál es la fecha",
    "cual es el día de hoy",
    "cual es el dia de hoy",
    "cuál es el día de hoy",
    "cuál es el dia de hoy",
    "que dia es hoy",
    "qué dia es hoy",
    "que día es hoy",
    "qué día es hoy",
    "que dia es",
    "qué dia es",
    "que día es",
    "qué día es",
    "que dia estamos",
    "qué dia estamos",
    "que día estamos",
    "qué día estamos",
    "en que dia estamos hoy",
    "en que día estamos hoy",
    "en qué dia estamos hoy",
    "en qué día estamos hoy",
    "dime la fecha",
    "me dices la fecha",
    "fecha actual",
    "sabes qué día es hoy",
    "sabes que dia es hoy",
    "en que fecha estamos",
    "en qué fecha estamos",
})

# Puntuacion que Whisper anade con frecuencia a la transcripcion
# ("¡Qué fecha es hoy!", "¿Qué hora es?") y que no debe romper la
# deteccion de intenciones de fecha/hora.
_PUNTUACION_VOZ = "¿¡?!.,;:"

_ELIPSIS = "…"


def _normalizar_voz(texto: str) -> str:
    """Normaliza una transcripcion para la deteccion local.

    Aplica, en orden: minusculas, quitar puntuacion de voz y espacios de
    los bordes (signos de pregunta/exclamacion, puntos, comas, puntos
    suspensivos) y colapsar espacios duplicados. Whisper suele anadir
    "¿...?" o "..." que no deben romper la deteccion.
    """
    t = texto.lower()
    t = t.strip()
    t = t.strip(_PUNTUACION_VOZ + _ELIPSIS)
    t = t.strip()
    return " ".join(t.split())


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

    t = _normalizar_voz(t)

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