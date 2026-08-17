"""Comandos relacionados con el navegador."""

import urllib.parse
import webbrowser


def es_comando_navegador(texto: str) -> bool:
    texto = texto.strip().lower()
    return (
        texto == "youtube"
        or texto.startswith("youtube ")
        or texto.startswith("busca ")
        or texto.startswith("chatgpt ")
    )


def _abrir(url: str) -> bool:
    """Abre una URL con el navegador predeterminado, sin depender del sistema operativo."""
    try:
        return webbrowser.open(url)
    except (OSError, webbrowser.Error):
        return False


def navegador_inteligente(texto: str) -> bool:
    texto = texto.strip().lower()

    if texto == "youtube":
        return _abrir("https://youtube.com")

    if texto.startswith("youtube "):
        consulta = texto.removeprefix("youtube ").strip()
        return _abrir(
            "https://youtube.com/results?search_query="
            + urllib.parse.quote_plus(consulta)
        )

    if texto.startswith("busca "):
        consulta = texto.removeprefix("busca ").strip()
        return _abrir("https://google.com/search?q=" + urllib.parse.quote_plus(consulta))

    if texto.startswith("chatgpt "):
        consulta = texto.removeprefix("chatgpt ").strip()
        return _abrir("https://chat.openai.com/?q=" + urllib.parse.quote_plus(consulta))

    return False


def buscar_en_web(consulta: str) -> bool:
    """Realiza una busqueda web generica (Google) para una consulta estructurada.

    La consulta se recibe como dato (no como texto de comando) y se
    codifica de forma segura antes de abrir el navegador.
    """
    consulta = consulta.strip()

    if not consulta:
        return False

    return _abrir(
        "https://google.com/search?q=" + urllib.parse.quote_plus(consulta)
    )
