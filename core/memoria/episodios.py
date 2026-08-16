from __future__ import annotations

from typing import Any

from core.conocimiento import normalizar_para_busqueda
from core.memoria.estructura import (
    CONFIANZA_USUARIO,
    _asegurar_diccionario,
    _asegurar_lista,
    _clave_recuerdo,
    _es_episodio_valido,
    _fecha_iso,
    _id_memoria,
    _limpiar_recuerdo,
    _normalizar_confianza,
    _normalizar_fuente,
)


def registrar_episodio(
    memoria: dict[str, Any],
    tipo: str,
    contenido: str,
    categoria: str = "otros",
    fuente: str = "usuario",
    confianza: float = CONFIANZA_USUARIO,
    fecha: str | None = None,
) -> bool:
    contenido_limpio = _limpiar_recuerdo(contenido)

    if not _es_episodio_valido(tipo, contenido_limpio):
        return False

    episodio = {
        "id": _id_memoria(tipo, categoria, contenido_limpio),
        "tipo": tipo,
        "contenido": contenido_limpio,
        "categoria": categoria or "otros",
        "fecha": fecha or _fecha_iso(),
        "creada_en": fecha or _fecha_iso(),
        "actualizada_en": fecha or _fecha_iso(),
        "estado": "activa",
        "fuente": _normalizar_fuente(fuente),
        "confianza": _normalizar_confianza(confianza),
    }
    episodica = _asegurar_diccionario(memoria, "episodica")
    eventos = _asegurar_lista(episodica, "eventos")

    if _episodio_duplicado(eventos, episodio):
        return False

    eventos.append(episodio)
    return True


def listar_memorias_activas(
    memoria: dict[str, Any],
    limite: int = 20,
) -> list[dict[str, Any]]:
    eventos = memoria.get("episodica", {}).get("eventos", [])

    if not isinstance(eventos, list) or limite <= 0:
        return []

    activas = [
        evento
        for evento in eventos
        if isinstance(evento, dict) and _episodio_activo(evento)
    ]
    return activas[-limite:]


def listar_memorias_olvidadas(
    memoria: dict[str, Any],
    limite: int = 20,
) -> list[dict[str, Any]]:
    eventos = memoria.get("episodica", {}).get("eventos", [])

    if not isinstance(eventos, list) or limite <= 0:
        return []

    olvidadas = [
        evento
        for evento in eventos
        if (
            isinstance(evento, dict)
            and evento.get("estado") == "olvidada"
            and normalizar_para_busqueda(str(evento.get("tipo", ""))) != "olvido"
        )
    ]
    return olvidadas[-limite:]


def buscar_memoria(memoria: dict[str, Any], memoria_id: str) -> dict[str, Any] | None:
    eventos = memoria.get("episodica", {}).get("eventos", [])
    if not isinstance(eventos, list):
        return None

    for evento in eventos:
        if isinstance(evento, dict) and str(evento.get("id", "")) == memoria_id:
            return evento
    return None


def olvidar_memoria(memoria: dict[str, Any], memoria_id: str) -> bool:
    return cambiar_estado_memoria(memoria, memoria_id, "olvidada")


def eliminar_memoria(memoria: dict[str, Any], memoria_id: str) -> bool:
    return cambiar_estado_memoria(memoria, memoria_id, "eliminada")


def cambiar_estado_memoria(
    memoria: dict[str, Any],
    memoria_id: str,
    estado: str,
) -> bool:
    if estado not in {"olvidada", "eliminada"}:
        return False

    evento = buscar_memoria(memoria, memoria_id)
    if not evento or evento.get("tipo") == "olvido":
        return False
    if evento.get("estado") == "eliminada":
        return False
    if evento.get("estado") == estado:
        return False

    evento["estado"] = estado
    evento["actualizada_en"] = _fecha_iso()
    _retirar_memoria_de_estructuras(memoria, evento)
    return True


def _episodio_activo(
    evento: dict[str, Any],
) -> bool:
    tipo = normalizar_para_busqueda(str(evento.get("tipo", "")))
    return tipo != "olvido" and evento.get("estado", "activa") == "activa"


def _episodio_duplicado(
    eventos: list[dict[str, Any]],
    episodio: dict[str, Any]
) -> bool:
    clave = _clave_episodio(episodio)

    for existente in eventos:
        if not isinstance(existente, dict):
            continue

        if _clave_episodio(existente) == clave:
            return True

    return False


def _clave_episodio(episodio: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalizar_para_busqueda(str(episodio.get("tipo", ""))),
        normalizar_para_busqueda(str(episodio.get("categoria", ""))),
        normalizar_para_busqueda(str(episodio.get("contenido", ""))),
    )


def _buscar_id_memoria_activa(
    memoria: dict[str, Any],
    tipo: str,
    contenidos: list[str],
    categorias: list[str],
) -> str:
    claves_contenido = {
        _clave_recuerdo(valor)
        for valor in contenidos
        if isinstance(valor, str) and valor.strip()
    }
    claves_categoria = {
        normalizar_para_busqueda(valor)
        for valor in categorias
        if valor
    }

    for evento in reversed(listar_memorias_activas(memoria, limite=100000)):
        if normalizar_para_busqueda(str(evento.get("tipo", ""))) != tipo:
            continue
        if _clave_recuerdo(evento.get("contenido", "")) not in claves_contenido:
            continue
        categoria = normalizar_para_busqueda(str(evento.get("categoria", "")))
        if claves_categoria and categoria not in claves_categoria:
            continue
        return str(evento.get("id", ""))
    return ""


def _retirar_memoria_de_estructuras(
    memoria: dict[str, Any],
    evento: dict[str, Any],
) -> None:
    tipo = normalizar_para_busqueda(str(evento.get("tipo", "")))
    categoria = str(evento.get("categoria", "otros"))
    contenido = str(evento.get("contenido", ""))
    usuario = memoria.get("usuario", {})

    if tipo == "gusto":
        valores = usuario.get("gustos", {}).get(categoria)
        if isinstance(valores, list):
            _eliminar_de_lista(valores, [contenido])
    elif tipo == "aprendizaje":
        valores = memoria.get("aprendizaje", {}).get(categoria)
        if isinstance(valores, list):
            _eliminar_de_lista(valores, [contenido])
    elif tipo == "objetivo":
        objetivos = usuario.get("objetivos", [])
        if isinstance(objetivos, list):
            _eliminar_de_lista(objetivos, [contenido])
    elif tipo == "herramienta":
        valores = usuario.get("herramientas", {}).get(categoria)
        if isinstance(valores, list):
            _eliminar_de_lista(valores, [contenido])
    elif tipo == "proyecto":
        proyectos = memoria.get("proyectos", {})
        if isinstance(proyectos, dict):
            for nombre in list(proyectos):
                if _clave_recuerdo(nombre) == _clave_recuerdo(contenido):
                    proyectos.pop(nombre, None)

    if not _hay_otra_memoria_activa_con_contenido(memoria, evento):
        _olvidar_preferencias(memoria, [contenido])
        _olvidar_entidades(memoria, [contenido])


def _hay_otra_memoria_activa_con_contenido(
    memoria: dict[str, Any],
    excluida: dict[str, Any],
) -> bool:
    clave = _clave_recuerdo(excluida.get("contenido", ""))
    excluida_id = str(excluida.get("id", ""))
    return any(
        str(evento.get("id", "")) != excluida_id
        and _clave_recuerdo(evento.get("contenido", "")) == clave
        for evento in listar_memorias_activas(memoria, limite=100000)
    )


def _eliminar_de_lista(lista: list[str], candidatos: list[str]) -> bool:
    claves = {
        normalizar_para_busqueda(candidato)
        for candidato in candidatos
        if _limpiar_recuerdo(candidato)
    }
    longitud_inicial = len(lista)

    lista[:] = [
        valor
        for valor in lista
        if normalizar_para_busqueda(str(valor)) not in claves
    ]

    return len(lista) != longitud_inicial


def _olvidar_preferencias(
    memoria: dict[str, Any],
    candidatos: list[str]
) -> None:
    preferencias = memoria.get("usuario", {}).get("preferencias", {})

    if not isinstance(preferencias, dict):
        return

    claves = {
        normalizar_para_busqueda(candidato)
        for candidato in candidatos
        if _limpiar_recuerdo(candidato)
    }

    for clave, valor in list(preferencias.items()):
        if normalizar_para_busqueda(str(valor)) in claves:
            preferencias.pop(clave, None)


def _olvidar_entidades(
    memoria: dict[str, Any],
    candidatos: list[str]
) -> None:
    semantica = memoria.get("semantica", {})
    entidades = semantica.get("entidades", {})

    if not isinstance(entidades, dict):
        return

    claves = {
        normalizar_para_busqueda(candidato)
        for candidato in candidatos
        if _limpiar_recuerdo(candidato)
    }

    for nombre in list(entidades):
        if normalizar_para_busqueda(str(nombre)) in claves:
            entidades.pop(nombre, None)

    relaciones = semantica.get("relaciones", [])

    if isinstance(relaciones, list):
        relaciones[:] = [
            relacion
            for relacion in relaciones
            if not (
                isinstance(relacion, dict)
                and (
                    normalizar_para_busqueda(
                        str(relacion.get("origen", ""))
                    ) in claves
                    or normalizar_para_busqueda(
                        str(relacion.get("destino", ""))
                    ) in claves
                )
            )
        ]

