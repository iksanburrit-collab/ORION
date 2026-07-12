from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
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


CATEGORIAS_HERRAMIENTAS_MEMORIA = (
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


ALIAS_GUSTOS = {
    "musica": "musica",
    "música": "musica",
    "canciones": "musica",
    "rolas": "musica",
    "comidas": "comida",
    "comer": "comida",
    "deporte": "deportes",
    "deportes": "deportes",
    "juego": "videojuegos",
    "juegos": "videojuegos",
    "videojuego": "videojuegos",
    "videojuegos": "videojuegos",
    "gaming": "videojuegos",
    "pelicula": "peliculas",
    "peliculas": "peliculas",
    "serie": "series",
}


PALABRAS_CLAVE_GUSTOS = {
    "videojuegos": {
        "videojuego",
        "videojuegos",
        "juego",
        "juegos",
        "gaming",
        "gamer",
        "steam",
        "consola",
        "pc",
        "sandbox",
        "survival",
        "shooter",
        "rpg",
        "moba",
        "battle",
        "royale",
        "craft",
        "factory",
        "factorio",
        "arena",
        "breakout",
        "simulador",
        "automatizacion",
        "automatización",
    },
    "deportes": {
        "deporte",
        "deportes",
        "futbol",
        "fútbol",
        "voleibol",
        "voley",
        "volley",
        "basquet",
        "basket",
        "tenis",
        "natacion",
        "natación",
        "correr",
        "ciclismo",
        "box",
        "boxeo",
        "entrenar",
    },
    "comida": {
        "comida",
        "comidas",
        "comer",
        "pizza",
        "pasta",
        "taco",
        "tacos",
        "sushi",
        "ramen",
        "hamburguesa",
        "sopa",
        "ensalada",
        "pollo",
        "carne",
        "arroz",
        "queso",
        "pan",
        "postre",
        "helado",
    },
    "musica": {
        "musica",
        "música",
        "cancion",
        "canción",
        "canciones",
        "rola",
        "rolas",
        "genero",
        "género",
        "banda",
        "artista",
        "album",
        "álbum",
        "rock",
        "pop",
        "rap",
        "trap",
        "reggaeton",
        "jazz",
        "metal",
        "clasica",
        "clásica",
    },
    "tecnologia": {
        "tecnologia",
        "tecnología",
        "programacion",
        "programación",
        "codigo",
        "código",
        "software",
        "hardware",
        "linux",
        "windows",
        "python",
        "javascript",
        "git",
        "vscode",
        "vs code",
        "docker",
        "ia",
        "inteligencia artificial",
    },
    "peliculas": {
        "pelicula",
        "peliculas",
        "cine",
        "film",
        "saga",
    },
    "series": {
        "serie",
        "series",
        "temporada",
        "episodio",
        "anime",
    },
}


PATRONES_GUSTOS = {
    "videojuegos": (
        r"\b\w*factory\w*\b",
        r"\b\w+craft\b",
        r"\b\w+quest\b",
        r"\b\w+vania\b",
        r"\b\w+io\b",
    ),
    "comida": (
        r"\b\w+(?:burger|pizza|sushi|taco|ramen)\b",
    ),
    "musica": (
        r"\b\w+(?:core|wave|pop|rock|metal|rap|trap)\b",
    ),
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


CATEGORIAS_HERRAMIENTAS = {
    "lenguajes": CATEGORIAS_APRENDIZAJE["lenguajes"],
    "tecnologia": {
        "Linux",
        "Windows",
        "Git",
        "VS Code",
        "Excel",
        "Blender",
        "Unity",
        "Godot",
        "Docker",
        "Arduino",
        "Factorio",
    },
}


RELACIONES_SEMANTICAS = {
    "minecraft": ("videojuego",),
    "factorio": ("videojuego", "automatizacion"),
    "roblox": ("videojuego",),
    "fortnite": ("videojuego",),
    "valorant": ("videojuego",),
    "terraria": ("videojuego",),
    "stardew valley": ("videojuego",),
    "python": ("lenguaje", "programacion"),
    "javascript": ("lenguaje", "programacion"),
    "java": ("lenguaje", "programacion"),
    "c++": ("lenguaje", "programacion"),
    "c#": ("lenguaje", "programacion"),
    "html": ("lenguaje", "desarrollo web"),
    "css": ("lenguaje", "desarrollo web"),
    "sql": ("lenguaje", "bases de datos"),
    "rust": ("lenguaje", "programacion"),
    "go": ("lenguaje", "programacion"),
    "git": ("control de versiones", "tecnologia"),
    "docker": ("contenedores", "tecnologia"),
    "linux": ("sistema operativo", "tecnologia"),
    "windows": ("sistema operativo", "tecnologia"),
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
    confianza: float = 1.0


@dataclass(frozen=True)
class ClasificacionGusto:
    categoria: str
    valor: str
    confianza: float
    razones: tuple[str, ...] = ()

    def __iter__(self):
        yield self.categoria
        yield self.valor


def detectar_conocimiento(texto: str) -> ConocimientoDetectado | None:
    texto_limpio = limpiar_valor(texto)
    texto_normalizado = normalizar_para_busqueda(texto_limpio)

    aprendizaje = _detectar_aprendizaje(texto_limpio, texto_normalizado)

    if aprendizaje:
        return aprendizaje

    gusto = _detectar_gusto(texto_limpio, texto_normalizado)

    if gusto:
        return gusto

    herramienta = _detectar_herramienta(texto_limpio, texto_normalizado)

    if herramienta:
        return herramienta

    return _detectar_objetivo(texto_limpio, texto_normalizado)


def clasificar_gusto(
    valor: str,
    texto_original: str = "",
    categoria_contexto: str | None = None,
) -> ClasificacionGusto:
    valor_limpio = limpiar_valor(valor)

    if (
        categoria_contexto is None
        and texto_original in CATEGORIAS_GUSTOS_MEMORIA
    ):
        categoria_contexto = texto_original
        texto_original = valor_limpio

    texto_original = texto_original or valor_limpio
    categoria_contexto = _normalizar_categoria_gusto(categoria_contexto)

    if categoria_contexto in CATEGORIAS_GUSTOS_MEMORIA:
        return ClasificacionGusto(
            categoria_contexto,
            _canonizar_valor(
                valor_limpio,
                CATEGORIAS_GUSTOS.get(categoria_contexto, set()),
            ),
            1.0,
            ("contexto_explicito",),
        )

    categoria_detectada = _clasificar_por_diccionario(
        valor_limpio,
        CATEGORIAS_GUSTOS
    )

    if categoria_detectada:
        categoria, valor_canonico = categoria_detectada
        return ClasificacionGusto(
            categoria,
            valor_canonico,
            1.0,
            ("entidad_conocida",),
        )

    return _clasificar_gusto_por_reglas(valor_limpio, texto_original)


def _clasificar_gusto_por_reglas(
    valor: str,
    texto_original: str,
) -> ClasificacionGusto:
    valor_normalizado = normalizar_para_busqueda(valor)
    texto_normalizado = normalizar_para_busqueda(texto_original)
    texto_combinado = f"{texto_normalizado} {valor_normalizado}".strip()
    puntuaciones: dict[str, float] = {}
    razones: dict[str, list[str]] = {}

    def sumar(categoria: str, puntos: float, razon: str) -> None:
        puntuaciones[categoria] = puntuaciones.get(categoria, 0.0) + puntos
        razones.setdefault(categoria, []).append(razon)

    for alias, categoria in ALIAS_GUSTOS.items():
        alias_normalizado = normalizar_para_busqueda(alias)

        if _contiene_termino(texto_combinado, alias_normalizado):
            sumar(categoria, 1.2, f"alias:{alias_normalizado}")

    for categoria, palabras in PALABRAS_CLAVE_GUSTOS.items():
        for palabra in palabras:
            palabra_normalizada = normalizar_para_busqueda(palabra)

            if _contiene_termino(valor_normalizado, palabra_normalizada):
                sumar(categoria, 1.1, f"valor:{palabra_normalizada}")
            elif _contiene_termino(texto_normalizado, palabra_normalizada):
                sumar(categoria, 0.7, f"contexto:{palabra_normalizada}")

    for categoria, patrones in PATRONES_GUSTOS.items():
        for patron in patrones:
            if re.search(patron, valor_normalizado):
                sumar(categoria, 1.05, f"patron:{patron}")

    _sumar_por_contexto_frase(texto_normalizado, sumar)

    if not puntuaciones:
        return ClasificacionGusto(
            "otros",
            _formatear_desconocido(valor),
            0.25,
            ("sin_senales_suficientes",),
        )

    ordenadas = sorted(
        puntuaciones.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    categoria, puntuacion = ordenadas[0]
    segunda = ordenadas[1][1] if len(ordenadas) > 1 else 0.0

    if puntuacion < 1.0 or puntuacion - segunda < 0.35:
        return ClasificacionGusto(
            "otros",
            _formatear_desconocido(valor),
            min(0.5, puntuacion / 3.0),
            tuple(razones.get(categoria, ("clasificacion_ambigua",))),
        )

    confianza = min(0.9, 0.45 + puntuacion / 4.0)
    return ClasificacionGusto(
        categoria,
        _formatear_desconocido(valor),
        confianza,
        tuple(razones.get(categoria, ())),
    )


def _sumar_por_contexto_frase(
    texto_normalizado: str,
    sumar: Any,
) -> None:
    reglas = (
        ("videojuegos", ("juego", "juegos", "videojuego", "videojuegos")),
        ("deportes", ("deporte", "deportes", "jugar al", "practicar")),
        ("comida", ("comer", "comida", "platillo", "postre")),
        ("musica", ("escuchar", "musica", "cancion", "banda", "artista")),
        ("tecnologia", ("programar", "codigo", "software", "tecnologia")),
        ("peliculas", ("ver peliculas", "cine", "pelicula")),
        ("series", ("ver series", "serie", "anime")),
    )

    for categoria, pistas in reglas:
        for pista in pistas:
            if _contiene_termino(texto_normalizado, pista):
                sumar(categoria, 0.9, f"frase:{pista}")


def _normalizar_categoria_gusto(categoria: str | None) -> str | None:
    if not categoria:
        return None

    categoria_normalizada = normalizar_para_busqueda(categoria)
    return ALIAS_GUSTOS.get(categoria_normalizada, categoria_normalizada)


def _contiene_termino(texto: str, termino: str) -> bool:
    if not texto or not termino:
        return False

    if " " in termino:
        return termino in texto

    return bool(re.search(rf"\b{re.escape(termino)}\b", texto))


def clasificar_aprendizaje(valor: str) -> tuple[str, str]:
    valor_limpio = limpiar_valor(valor)
    categoria_detectada = _clasificar_por_diccionario(
        valor_limpio,
        CATEGORIAS_APRENDIZAJE
    )

    if categoria_detectada:
        return categoria_detectada

    return "otros", _formatear_desconocido(valor_limpio)


def clasificar_herramienta(valor: str) -> tuple[str, str]:
    valor_limpio = limpiar_valor(valor)
    categoria_detectada = _clasificar_por_diccionario(
        valor_limpio,
        CATEGORIAS_HERRAMIENTAS
    )

    if categoria_detectada:
        return categoria_detectada

    return "otros", _formatear_desconocido(valor_limpio)


def inferir_relaciones_semanticas(
    valor: str,
    categoria: str,
    tipo: str
) -> list[dict[str, str]]:
    valor_normalizado = normalizar_para_busqueda(valor)
    relaciones = []

    for entidad, conceptos in RELACIONES_SEMANTICAS.items():
        if valor_normalizado != entidad:
            continue

        for concepto in conceptos:
            relaciones.append({
                "origen": valor,
                "relacion": "es_un",
                "destino": concepto,
                "fuente": tipo,
            })

    if categoria and categoria != "otros":
        relaciones.append({
            "origen": valor,
            "relacion": "pertenece_a",
            "destino": categoria,
            "fuente": tipo,
        })

    return relaciones


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
        r"^prefiero\s+(?P<valor>.+)$",
        r"^mi\s+favorit[oa]\s+es\s+(?P<valor>.+)$",
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
        clasificacion = clasificar_gusto(
            valor,
            texto_limpio,
            categoria_contexto,
        )
        categoria = clasificacion.categoria
        valor_canonico = clasificacion.valor
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
            confianza=clasificacion.confianza,
        )

    return None


def _detectar_aprendizaje(
    texto_limpio: str,
    texto_normalizado: str
) -> ConocimientoDetectado | None:
    patrones_aprendizaje = (
        r"^(?:estoy|ando)\s+aprendiendo\s+(?P<valor>.+)$",
        r"^quiero\s+aprender\s+(?P<valor>.+)$",
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


def _detectar_objetivo(
    texto_limpio: str,
    texto_normalizado: str
) -> ConocimientoDetectado | None:
    patrones_objetivo = (
        r"^mi\s+objetivo\s+es\s+(?P<valor>.+)$",
        r"^quiero\s+(?P<valor>.+)$",
    )

    for patron in patrones_objetivo:
        coincidencia = re.match(patron, texto_normalizado)

        if not coincidencia:
            continue

        valor = _extraer_valor_original(
            texto_limpio,
            coincidencia.group("valor")
        )

        return ConocimientoDetectado(
            tipo="objetivo",
            categoria="otros",
            valor=_formatear_desconocido(valor),
        )

    return None


def _detectar_herramienta(
    texto_limpio: str,
    texto_normalizado: str
) -> ConocimientoDetectado | None:
    patrones_herramienta = (
        r"^trabajo\s+con\s+(?P<valor>.+)$",
        r"^uso\s+(?P<valor>.+)$",
    )

    for patron in patrones_herramienta:
        coincidencia = re.match(patron, texto_normalizado)

        if not coincidencia:
            continue

        valor = _extraer_valor_original(
            texto_limpio,
            coincidencia.group("valor")
        )
        categoria, valor_canonico = clasificar_herramienta(valor)

        return ConocimientoDetectado(
            tipo="herramienta",
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
