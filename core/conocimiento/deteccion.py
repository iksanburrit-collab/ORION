from __future__ import annotations

import re

from core.conocimiento.terminos import (
    CATEGORIA_POR_CONTEXTO,
    ConocimientoDetectado,
)
from core.conocimiento.normalizacion import (
    _extraer_valor_original,
    _formatear_desconocido,
    limpiar_valor,
    normalizar_para_busqueda,
)
from core.conocimiento.clasificacion import (
    clasificar_aprendizaje,
    clasificar_gusto,
    clasificar_herramienta,
)


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

