"""
Comandos relacionados con el navegador.
"""

import os
import urllib.parse


def navegador_inteligente(t):

    if t == "youtube":

        os.startfile(
            "https://youtube.com"
        )

        return True

    if t.startswith("youtube "):

        q = t.replace(
            "youtube ",
            ""
        )

        os.startfile(
            "https://youtube.com/results?search_query="
            + urllib.parse.quote(q)
        )

        return True

    if t.startswith("busca "):

        q = t.replace(
            "busca ",
            ""
        )

        os.startfile(
            "https://google.com/search?q="
            + urllib.parse.quote(q)
        )

        return True

    if t.startswith("chatgpt "):

        q = t.replace(
            "chatgpt ",
            ""
        )

        os.startfile(
            "https://chat.openai.com/chat"
            + urllib.parse.quote(q)
        )

        return True

    return False
