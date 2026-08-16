from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.conocimiento import (
    CATEGORIAS_GUSTOS_MEMORIA,
    clasificar_gusto,
    detectar_conocimiento,
    normalizar_para_busqueda,
)
from core.memoria.episodios import (
    _episodio_activo,
    _episodio_duplicado,
    _retirar_memoria_de_estructuras,
    registrar_episodio,
)
from core.memoria.estructura import (
    CONFIANZA_INFERENCIA,
    CONFIANZA_USUARIO,
    _agregar_unico,
    _asegurar_diccionario,
    _asegurar_lista,
    _asegurar_perfil,
    _asegurar_raiz,
    _asegurar_usuario,
    _clave_recuerdo,
    _es_episodio_valido,
    _fecha_iso,
    _id_memoria,
    _limpiar_recuerdo,
    _normalizar_confianza,
    _normalizar_conversacion,
    _normalizar_fuente,
    _sincronizar_compatibilidad,
)
from core.memoria.operaciones import (
    registrar_conocimiento_semantico,
    registrar_gusto,
)


def inicializar_memoria(memoria: dict[str, Any] | None) -> dict[str, Any]:

    if not isinstance(memoria, dict):
        memoria = {}

    _asegurar_perfil(memoria)
    _asegurar_usuario(memoria)
    _asegurar_raiz(memoria)
    _migrar_memoria_legacy(memoria)
    _limpiar_memoria_funcional(memoria)
    _actualizar_indice_memorias(memoria)
    _sincronizar_compatibilidad(memoria)

    return memoria


def _migrar_memoria_legacy(memoria: dict[str, Any]) -> None:

    perfil = memoria["perfil"]
    contexto = memoria["contexto"]

    if not perfil["nombre"] and isinstance(memoria.get("nombre"), str):
        perfil["nombre"] = memoria["nombre"]

    if (
        not perfil["fecha_nacimiento"]
        and isinstance(memoria.get("fecha_nacimiento"), str)
    ):
        perfil["fecha_nacimiento"] = memoria["fecha_nacimiento"]

    if (
        not contexto["ultimo_comando"]
        and isinstance(memoria.get("ultimo_comando"), str)
    ):
        contexto["ultimo_comando"] = memoria["ultimo_comando"]

    if (
        not contexto["ultimo_contexto"]
        and isinstance(memoria.get("ultimo_contexto"), str)
    ):
        contexto["ultimo_contexto"] = memoria["ultimo_contexto"]

    frases_legacy = memoria.get("frases_importantes")

    if isinstance(frases_legacy, list):
        aprendizaje = memoria["aprendizaje"]
        aprendizaje.setdefault(
            "frases_importantes_legacy",
            deepcopy(frases_legacy)
        )

        for frase in frases_legacy:
            if not isinstance(frase, str):
                continue

            conocimiento = detectar_conocimiento(frase)

            if conocimiento and conocimiento.tipo == "gusto":
                registrar_gusto(
                    memoria,
                    conocimiento.categoria,
                    conocimiento.valor
                )
                registrar_conocimiento_semantico(memoria, conocimiento)


def _limpiar_memoria_funcional(memoria: dict[str, Any]) -> None:
    usuario = memoria.get("usuario", {})

    for valores in usuario.get("gustos", {}).values():
        if isinstance(valores, list):
            _normalizar_lista_recuerdos(valores)

    _reclasificar_gustos(memoria)

    for valores in memoria.get("aprendizaje", {}).values():
        if isinstance(valores, list):
            _normalizar_lista_recuerdos(valores)

    for valores in usuario.get("herramientas", {}).values():
        if isinstance(valores, list):
            _normalizar_lista_recuerdos(valores)

    objetivos = usuario.get("objetivos")

    if isinstance(objetivos, list):
        _normalizar_lista_recuerdos(objetivos)

    eventos = memoria.get("episodica", {}).get("eventos", [])

    if isinstance(eventos, list):
        _normalizar_episodios(eventos)

    conversacion = memoria.get("conversacion", [])

    if isinstance(conversacion, list):
        _normalizar_conversacion(conversacion)


def _reclasificar_gustos(memoria: dict[str, Any]) -> None:
    gustos = memoria.get("usuario", {}).get("gustos", {})

    if not isinstance(gustos, dict):
        return

    nuevos = {
        categoria: []
        for categoria in CATEGORIAS_GUSTOS_MEMORIA
    }
    ubicaciones: dict[str, str] = {}
    conservados_otros = []

    for categoria, valores in list(gustos.items()):
        if not isinstance(valores, list):
            continue

        categoria_actual = (
            categoria
            if categoria in CATEGORIAS_GUSTOS_MEMORIA
            else "otros"
        )

        for valor in valores:
            valor_limpio = _limpiar_recuerdo(valor)

            if not valor_limpio:
                continue

            destino = _categoria_migrada_gusto(categoria_actual, valor_limpio)
            _agregar_gusto_migrado(nuevos, ubicaciones, destino, valor_limpio)

            if categoria_actual == "otros" and destino == "otros":
                _agregar_unico(conservados_otros, valor_limpio)

    gustos.clear()
    gustos.update(nuevos)

    if conservados_otros:
        sistema = _asegurar_diccionario(memoria, "sistema")
        migracion = _asegurar_diccionario(sistema, "migracion_v6")
        copia = _asegurar_lista(migracion, "conservados_otros")

        for valor in conservados_otros:
            _agregar_unico(copia, valor)


def _categoria_migrada_gusto(categoria_actual: str, valor: str) -> str:
    clasificacion = clasificar_gusto(valor)

    if (
        clasificacion.categoria != "otros"
        and clasificacion.confianza >= CONFIANZA_INFERENCIA
    ):
        return clasificacion.categoria

    if categoria_actual in CATEGORIAS_GUSTOS_MEMORIA:
        return categoria_actual

    return "otros"


def _agregar_gusto_migrado(
    gustos: dict[str, list[str]],
    ubicaciones: dict[str, str],
    categoria: str,
    valor: str,
) -> None:
    clave = _clave_recuerdo(valor)
    existente = ubicaciones.get(clave)

    if existente == categoria:
        _agregar_unico(gustos[categoria], valor)
        return

    if existente and existente != "otros":
        return

    if existente == "otros" and categoria != "otros":
        gustos["otros"] = [
            actual
            for actual in gustos["otros"]
            if _clave_recuerdo(actual) != clave
        ]

    ubicaciones[clave] = categoria
    _agregar_unico(gustos[categoria], valor)


def _normalizar_lista_recuerdos(lista: list[Any]) -> None:
    vistos = set()
    limpios = []

    for valor in lista:
        valor_limpio = _limpiar_recuerdo(valor)

        if not valor_limpio:
            continue

        clave = _clave_recuerdo(valor_limpio)

        if clave in vistos:
            continue

        vistos.add(clave)
        limpios.append(valor_limpio)

    lista[:] = limpios


def _normalizar_episodios(eventos: list[Any]) -> None:
    limpios = []

    for evento in eventos:
        if not isinstance(evento, dict):
            continue

        contenido = _limpiar_recuerdo(evento.get("contenido", ""))
        tipo = str(evento.get("tipo", "")).strip().lower()

        if not _es_episodio_valido(tipo, contenido):
            continue

        categoria = str(evento.get("categoria", "otros") or "otros")
        creada_en = str(evento.get("creada_en") or evento.get("fecha") or _fecha_iso())
        estado = str(evento.get("estado", "activa"))
        if estado not in {"activa", "olvidada", "eliminada"}:
            estado = "activa"

        normalizado = {
            "id": str(evento.get("id") or _id_memoria(tipo, categoria, contenido)),
            "tipo": tipo,
            "contenido": contenido,
            "categoria": categoria,
            "fecha": str(evento.get("fecha") or creada_en),
            "creada_en": creada_en,
            "actualizada_en": str(evento.get("actualizada_en") or creada_en),
            "estado": estado,
            "fuente": _normalizar_fuente(str(evento.get("fuente", "usuario"))),
            "confianza": _normalizar_confianza(
                evento.get("confianza", CONFIANZA_USUARIO)
            ),
        }
        if evento.get("referencia_id"):
            normalizado["referencia_id"] = str(evento["referencia_id"])

        if not _episodio_duplicado(limpios, normalizado):
            limpios.append(normalizado)

    eventos[:] = limpios


def _actualizar_indice_memorias(memoria: dict[str, Any]) -> None:
    eventos = memoria.get("episodica", {}).get("eventos", [])
    if not isinstance(eventos, list):
        return

    _aplicar_olvidos_legacy(memoria, eventos)
    for evento in eventos:
        if (
            isinstance(evento, dict)
            and evento.get("estado") in {"olvidada", "eliminada"}
            and evento.get("tipo") != "olvido"
        ):
            _retirar_memoria_de_estructuras(memoria, evento)

    _indexar_estructuras_legacy(memoria)
    sistema = _asegurar_diccionario(memoria, "sistema")
    sistema["version_indice_memorias"] = 1


def _aplicar_olvidos_legacy(
    memoria: dict[str, Any],
    eventos: list[Any],
) -> None:
    for posicion, olvido in enumerate(eventos):
        if not isinstance(olvido, dict) or olvido.get("tipo") != "olvido":
            continue
        if olvido.get("referencia_id"):
            olvido["estado"] = "eliminada"
            continue

        contenido = normalizar_para_busqueda(str(olvido.get("contenido", "")))
        categoria = normalizar_para_busqueda(str(olvido.get("categoria", "")))
        candidatos = []

        for evento in eventos[:posicion]:
            if not isinstance(evento, dict) or not _episodio_activo(evento):
                continue
            if normalizar_para_busqueda(str(evento.get("contenido", ""))) != contenido:
                continue
            categoria_evento = normalizar_para_busqueda(
                str(evento.get("categoria", ""))
            )
            if categoria and categoria_evento != categoria:
                continue
            candidatos.append(evento)

        if candidatos:
            objetivo = candidatos[-1]
            objetivo["estado"] = "olvidada"
            objetivo["actualizada_en"] = str(
                olvido.get("actualizada_en") or olvido.get("fecha") or _fecha_iso()
            )
            olvido["referencia_id"] = objetivo["id"]
            _retirar_memoria_de_estructuras(memoria, objetivo)

        olvido["estado"] = "eliminada"


def _indexar_estructuras_legacy(memoria: dict[str, Any]) -> None:
    usuario = memoria.get("usuario", {})

    for categoria, valores in usuario.get("gustos", {}).items():
        if isinstance(valores, list):
            for valor in valores:
                registrar_episodio(memoria, "gusto", valor, categoria=categoria)

    for categoria, valores in memoria.get("aprendizaje", {}).items():
        if isinstance(valores, list):
            for valor in valores:
                registrar_episodio(memoria, "aprendizaje", valor, categoria=categoria)

    for valor in usuario.get("objetivos", []):
        registrar_episodio(memoria, "objetivo", valor, categoria="otros")

    for categoria, valores in usuario.get("herramientas", {}).items():
        if isinstance(valores, list):
            for valor in valores:
                registrar_episodio(memoria, "herramienta", valor, categoria=categoria)

    proyectos = memoria.get("proyectos", {})
    if isinstance(proyectos, dict):
        for nombre in proyectos:
            registrar_episodio(memoria, "proyecto", str(nombre), categoria="proyectos")

