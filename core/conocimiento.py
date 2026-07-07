from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


CATEGORIAS_GUSTOS_MEMORIA = (
    "videojuegos",
    "deportes",
    "comida",
    "musica",
    "tecnologia",
    "peliculas",
    "series",
    "otros",
)


CATEGORIAS_APRENDIZAJE_MEMORIA = (
    "lenguajes",
    "tecnologia",
    "otros",
)


CATEGORIAS_GUSTOS = {
    "videojuegos": {
        "Minecraft",
        "Factorio",
        "Roblox",
        "Fortnite",
        "Valorant",
        "League of Legends",
        "Free Fire",
        "Call of Duty",
        "FIFA",
        "Terraria",
        "Stardew Valley",
    },
    "deportes": {
        "futbol",
        "voleibol",
        "basquetbol",
        "beisbol",
        "tenis",
        "natacion",
        "box",
        "ciclismo",
    },
    "comida": {
        "pizza",
        "hamburguesa",
        "tacos",
        "sushi",
        "pasta",
        "ramen",
        "pozole",
        "enchiladas",
        "mole",
    },
    "musica": {
        "rock",
        "pop",
        "rap",
        "trap",
        "reggaeton",
        "jazz",
        "clasica",
        "metal",
    },
    "tecnologia": {
        "Python",
        "JavaScript",
        "Linux",
        "Windows",
        "inteligencia artificial",
        "programacion",
        "robotica",
        "computadoras",
    },
    "peliculas": {
        "Iron Man",
        "Avengers",
        "Spider-Man",
        "Batman",
        "Star Wars",
        "Interestelar",
    },
    "series": {
        "Stranger Things",
        "Breaking Bad",
        "The Last of Us",
        "The Mandalorian",
    },
}


CATEGORIAS_APRENDIZAJE = {
    "lenguajes": {
        "Python",
        "JavaScript",
        "Java",
        "C++",
        "C#",
        "HTML",
        "CSS",
        "SQL",
        "PHP",
        "Rust",
        "Go",
    },
    "tecnologia": {
        "programacion",
        "inteligencia artificial",
        "robotica",
        "redes",
        "bases de datos",
        "desarrollo web",
        "machine learning",
    },
}


CATEGORIA_POR_CONTEXTO = {
    "videojuego": "videojuegos",
    "videojuegos": "videojuegos",
    "juego": "videojuegos",
    "juegos": "videojuegos",
    "deporte": "deportes",
    "deportes": "deportes",
    "comida": "comida",
    "musica": "musica",
    "cancion": "musica",
    "canciones": "musica",
    "artista": "musica",
    "tecnologia": "tecnologia",
    "lenguaje": "tecnologia",
    "lenguajes": "tecnologia",
    "pelicula": "peliculas",
    "peliculas": "peliculas",
    "serie": "series",
    "series": "series",
}


ARTICULOS_INICIALES = (
    "el ",
    "la ",
    "los ",
    "las ",
    "un ",
    "una ",
    "unos ",
    "unas ",
    "a ",
)


@dataclass(frozen=True)
class ConocimientoDetectado:
    tipo: str
    categoria: str
    valor: str
    clave_preferencia: str | None = None


def detectar_conocimiento(texto: str) -> ConocimientoDetectado | None:
    texto_limpio = limpiar_valor(texto)
    texto_normalizado = normalizar_para_busqueda(texto_limpio)

    aprendizaje = _detectar_aprendizaje(texto_limpio, texto_normalizado)

    if aprendizaje:
        return aprendizaje

    return _detectar_gusto(texto_limpio, texto_normalizado)


def clasificar_gusto(
    valor: str,
    categoria_contexto: str | None = None
) -> tuple[str, str]:
    valor_limpio = limpiar_valor(valor)

    if categoria_contexto in CATEGORIAS_GUSTOS_MEMORIA:
        return categoria_contexto, _canonizar_valor(
            valor_limpio,
            CATEGORIAS_GUSTOS.get(categoria_contexto, set())
        )

    categoria_detectada = _clasificar_por_diccionario(
        valor_limpio,
        CATEGORIAS_GUSTOS
    )

    if categoria_detectada:
        return categoria_detectada

    return "otros", _formatear_desconocido(valor_limpio)


def clasificar_aprendizaje(valor: str) -> tuple[str, str]:
    valor_limpio = limpiar_valor(valor)
    categoria_detectada = _clasificar_por_diccionario(
        valor_limpio,
        CATEGORIAS_APRENDIZAJE
    )

    if categoria_detectada:
        return categoria_detectada

    return "otros", _formatear_desconocido(valor_limpio)


def normalizar_para_busqueda(texto: str) -> str:
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    return re.sub(r"\s+", " ", texto)


def limpiar_valor(valor: str) -> str:
    valor = re.sub(r"[.!?¡¿]+$", "", valor.strip())

    for articulo in ARTICULOS_INICIALES:
        if normalizar_para_busqueda(valor).startswith(articulo):
            valor = valor[len(articulo):].strip()
            break

    return valor


def _detectar_gusto(
    texto_limpio: str,
    texto_normalizado: str
) -> ConocimientoDetectado | None:
    patrones_gusto = (
        r"^(?:a mi\s+)?me\s+(?:gusta|gustan|encanta|encantan|fascina|fascinan|interesa|interesan)\s+(?P<valor>.+)$",
        r"^mi\s+(?P<contexto>[a-z0-9\s]+?)\s+favorit[oa]\s+es\s+(?P<valor>.+)$",
    )

    for patron in patrones_gusto:
        coincidencia = re.match(patron, texto_normalizado)

        if not coincidencia:
            continue

        valor = _extraer_valor_original(
            texto_limpio,
            coincidencia.group("valor")
        )
        contexto = coincidencia.groupdict().get("contexto")
        categoria_contexto = CATEGORIA_POR_CONTEXTO.get(contexto or "")
        categoria, valor_canonico = clasificar_gusto(valor, categoria_contexto)
        clave_preferencia = None

        if contexto:
            clave_preferencia = normalizar_para_busqueda(contexto).replace(
                " ",
                "_"
            )

        return ConocimientoDetectado(
            tipo="gusto",
            categoria=categoria,
            valor=valor_canonico,
            clave_preferencia=clave_preferencia,
        )

    return None


def _detectar_aprendizaje(
    texto_limpio: str,
    texto_normalizado: str
) -> ConocimientoDetectado | None:
    patrones_aprendizaje = (
        r"^(?:estoy|ando)\s+aprendiendo\s+(?P<valor>.+)$",
        r"^aprendo\s+(?P<valor>.+)$",
    )

    for patron in patrones_aprendizaje:
        coincidencia = re.match(patron, texto_normalizado)

        if not coincidencia:
            continue

        valor = _extraer_valor_original(
            texto_limpio,
            coincidencia.group("valor")
        )
        categoria, valor_canonico = clasificar_aprendizaje(valor)

        return ConocimientoDetectado(
            tipo="aprendizaje",
            categoria=categoria,
            valor=valor_canonico,
        )

    return None


def _clasificar_por_diccionario(
    valor: str,
    categorias: dict[str, set[str]]
) -> tuple[str, str] | None:
    valor_normalizado = normalizar_para_busqueda(valor)

    for categoria, terminos in categorias.items():
        for termino in terminos:
            termino_normalizado = normalizar_para_busqueda(termino)

            if (
                valor_normalizado == termino_normalizado
                or re.search(
                    rf"\b{re.escape(termino_normalizado)}\b",
                    valor_normalizado
                )
            ):
                return categoria, termino

    return None


def _canonizar_valor(valor: str, terminos: set[str]) -> str:
    valor_normalizado = normalizar_para_busqueda(valor)

    for termino in terminos:
        if normalizar_para_busqueda(termino) == valor_normalizado:
            return termino

    return _formatear_desconocido(valor)


def _formatear_desconocido(valor: str) -> str:
    valor = limpiar_valor(valor)

    if not valor:
        return valor

    if valor.isupper():
        return valor

    return " ".join(
        palabra.capitalize()
        if palabra.islower()
        else palabra
        for palabra in valor.split()
    )


def _extraer_valor_original(texto_original: str, valor_normalizado: str) -> str:
    palabras_objetivo = valor_normalizado.strip().split()
    palabras_originales = texto_original.split()

    if not palabras_objetivo:
        return ""

    return " ".join(palabras_originales[-len(palabras_objetivo):])
