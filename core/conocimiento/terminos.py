from __future__ import annotations

from dataclasses import dataclass


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


ENTIDADES_CANONICAS = {
    "arena breakout": "Arena Breakout",
    "factorio": "Factorio",
    "minecraft": "Minecraft",
    "musica": "música",
    "música": "música",
    "vscode": "VS Code",
    "vs code": "VS Code",
    "visual studio code": "VS Code",
    "wosb": "World of Sea Battle",
    "world of sea battle": "World of Sea Battle",
    "python": "Python",
    "git": "Git",
}


ENTIDADES_CATEGORIAS_GUSTOS = {
    "arena breakout": "videojuegos",
    "factorio": "videojuegos",
    "minecraft": "videojuegos",
    "música": "musica",
    "musica": "musica",
    "world of sea battle": "videojuegos",
    "wosb": "videojuegos",
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
        "wosb",
        "sea battle",
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

