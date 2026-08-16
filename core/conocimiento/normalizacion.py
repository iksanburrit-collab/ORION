from __future__ import annotations

import re
import unicodedata

from core.conocimiento.terminos import (
    ARTICULOS_INICIALES,
    ENTIDADES_CANONICAS,
    RELACIONES_SEMANTICAS,
)


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


def canonizar_entidad(valor: str) -> str:
    valor_limpio = limpiar_valor(valor)
    valor_normalizado = normalizar_para_busqueda(valor_limpio)

    if valor_normalizado in ENTIDADES_CANONICAS:
        return ENTIDADES_CANONICAS[valor_normalizado]

    return valor_limpio


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

