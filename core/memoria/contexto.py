from __future__ import annotations

from typing import Any

from core.conocimiento import normalizar_para_busqueda
from core.memoria.episodios import _episodio_activo
from core.memoria.estructura import (
    _formatear_lista,
    _limpiar_texto_conversacion,
    _normalizar_confianza,
)


def seleccionar_recuerdos_relevantes(
    memoria: dict[str, Any],
    consulta: str = "",
    categoria: str = "",
    limite: int = 5,
) -> list[dict[str, Any]]:
    eventos = memoria.get("episodica", {}).get("eventos", [])

    if not isinstance(eventos, list) or limite <= 0:
        return []

    consulta_palabras = _palabras_clave(consulta)
    categoria_normalizada = normalizar_para_busqueda(categoria)
    puntuados = []

    for posicion, evento in enumerate(eventos):
        if not isinstance(evento, dict):
            continue
        if not _episodio_activo(evento):
            continue

        puntuacion = _puntuar_episodio(
            evento,
            consulta_palabras,
            categoria_normalizada,
            posicion,
            len(eventos),
        )
        puntuados.append((puntuacion, evento))

    puntuados.sort(key=lambda item: item[0], reverse=True)
    return [evento for _, evento in puntuados[:limite]]


def construir_contexto_para_ia(
    memoria: dict[str, Any],
    consulta: str = "",
    limite: int = 1200,
) -> str:
    if limite <= 0:
        return ""

    lineas_prioritarias = _lineas_perfil(memoria)
    lineas_relacionadas = (
        _lineas_gustos_relacionados(memoria, consulta)
        + _lineas_aprendizaje_relacionado(memoria, consulta)
        + _lineas_objetivos(memoria)
        + _lineas_proyectos(memoria)
    )
    recuerdos = seleccionar_recuerdos_relevantes(
        memoria,
        consulta=consulta,
        limite=6,
    )
    lineas_recuerdos = [
        (
            "Recuerdo: "
            f"{evento.get('tipo', '')} - {evento.get('contenido', '')} "
            f"({evento.get('fuente', 'usuario')}, "
            f"confianza {evento.get('confianza', 1.0)})"
        )
        for evento in recuerdos
    ]
    lineas_conversacion = _lineas_conversacion_reciente(memoria, consulta)
    lineas = (
        [f"Consulta actual: {consulta}"] if consulta else []
    ) + lineas_prioritarias + lineas_relacionadas + lineas_recuerdos + lineas_conversacion

    return _aplicar_limite_contexto(lineas, limite)


def _palabras_clave(texto: str) -> set[str]:
    texto_normalizado = normalizar_para_busqueda(texto)
    palabras = set()

    for palabra in texto_normalizado.split():
        if len(palabra) <= 2:
            continue

        palabras.add(palabra)

    return palabras


def _puntuar_episodio(
    evento: dict[str, Any],
    consulta_palabras: set[str],
    categoria: str,
    posicion: int,
    total: int,
) -> float:
    contenido = normalizar_para_busqueda(str(evento.get("contenido", "")))
    categoria_evento = normalizar_para_busqueda(
        str(evento.get("categoria", ""))
    )
    tipo = normalizar_para_busqueda(str(evento.get("tipo", "")))
    texto_evento = f"{contenido} {categoria_evento} {tipo}"
    coincidencias = sum(
        1 for palabra in consulta_palabras if palabra in texto_evento
    )
    puntuacion = coincidencias * 4.0

    if categoria and categoria == categoria_evento:
        puntuacion += 3.0

    if evento.get("fuente") == "usuario":
        puntuacion += 2.0

    puntuacion += _normalizar_confianza(evento.get("confianza", 0.0)) * 2.0
    puntuacion += _puntuar_recencia(posicion, total)
    return puntuacion


def _puntuar_recencia(posicion: int, total: int) -> float:
    if total <= 1:
        return 1.0

    return posicion / (total - 1)


def _lineas_perfil(memoria: dict[str, Any]) -> list[str]:
    perfil = memoria.get("perfil", {})
    lineas = []

    nombre = perfil.get("nombre")

    if nombre:
        lineas.append(f"Perfil: nombre {nombre}")

    alias = perfil.get("alias")

    if alias:
        lineas.append(f"Alias: {alias}")

    return lineas


def _lineas_gustos_relacionados(
    memoria: dict[str, Any],
    consulta: str
) -> list[str]:
    gustos = memoria.get("usuario", {}).get("gustos", {})
    return _lineas_mapa_relacionado("Gustos", gustos, consulta)


def _lineas_aprendizaje_relacionado(
    memoria: dict[str, Any],
    consulta: str
) -> list[str]:
    aprendizaje = memoria.get("aprendizaje", {})
    return _lineas_mapa_relacionado("Aprendizaje", aprendizaje, consulta)


def _lineas_conversacion_reciente(
    memoria: dict[str, Any],
    consulta: str,
    limite: int = 3,
) -> list[str]:
    conversacion = memoria.get("conversacion", [])

    if not isinstance(conversacion, list) or limite <= 0:
        return []

    palabras = _palabras_clave(consulta)
    turnos = []

    for posicion, turno in enumerate(conversacion):
        if not isinstance(turno, dict):
            continue

        usuario = _limpiar_texto_conversacion(turno.get("usuario", ""))
        orion = _limpiar_texto_conversacion(turno.get("orion", ""))

        if not usuario or not orion:
            continue

        texto = normalizar_para_busqueda(f"{usuario} {orion}")
        coincidencias = sum(1 for palabra in palabras if palabra in texto)
        puntuacion = coincidencias * 3 + posicion
        turnos.append((puntuacion, usuario, orion))

    turnos.sort(key=lambda item: item[0], reverse=True)
    return [
        f"Conversacion reciente: usuario dijo {usuario}; ORION respondio {orion}"
        for _, usuario, orion in turnos[:limite]
    ]


def _lineas_mapa_relacionado(
    titulo: str,
    datos: dict[str, Any],
    consulta: str
) -> list[str]:
    if not isinstance(datos, dict):
        return []

    palabras = _palabras_clave(consulta)
    lineas = []

    for categoria, valores in datos.items():
        if not isinstance(valores, list) or not valores:
            continue

        valores_filtrados = _filtrar_valores_relacionados(
            valores,
            str(categoria),
            palabras,
        )

        if valores_filtrados:
            lineas.append(
                f"{titulo} {categoria}: {', '.join(valores_filtrados)}"
            )

    return lineas


def _filtrar_valores_relacionados(
    valores: list[Any],
    categoria: str,
    palabras: set[str]
) -> list[str]:
    limpios = [
        str(valor)
        for valor in valores
        if isinstance(valor, str) and valor.strip()
    ]

    if not palabras:
        return limpios[:5]

    relacionados = []

    for valor in limpios:
        texto = normalizar_para_busqueda(f"{categoria} {valor}")

        if any(palabra in texto for palabra in palabras):
            relacionados.append(valor)

    return relacionados[:5]


def _lineas_objetivos(memoria: dict[str, Any]) -> list[str]:
    objetivos = [
        objetivo
        for objetivo in memoria.get("usuario", {}).get("objetivos", [])
        if isinstance(objetivo, str) and objetivo.strip()
    ][:3]
    texto = _formatear_lista(objetivos)

    if texto:
        return [f"Objetivos: {texto}"]

    return []


def _lineas_proyectos(memoria: dict[str, Any]) -> list[str]:
    proyectos_datos = memoria.get("proyectos", {})

    if isinstance(proyectos_datos, dict) and proyectos_datos:
        proyectos = ", ".join(str(nombre) for nombre in list(proyectos_datos)[:3])
    elif isinstance(proyectos_datos, list) and proyectos_datos:
        proyectos = _formatear_lista(proyectos_datos[:3])
    else:
        proyectos = "No tengo proyectos guardados"

    if proyectos == "No tengo proyectos guardados":
        return []

    return [f"Proyectos: {proyectos}"]


def _aplicar_limite_contexto(lineas: list[str], limite: int) -> str:
    usadas = []
    longitud = 0

    for linea in lineas:
        if not linea:
            continue

        extra = len(linea) + (1 if usadas else 0)

        if longitud + extra > limite:
            break

        usadas.append(linea)
        longitud += extra

    return "\n".join(usadas)

