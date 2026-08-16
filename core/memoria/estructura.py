from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any

from core.conocimiento import (
    CATEGORIAS_APRENDIZAJE_MEMORIA,
    CATEGORIAS_GUSTOS_MEMORIA,
    CATEGORIAS_HERRAMIENTAS_MEMORIA,
    canonizar_entidad,
    limpiar_valor,
    normalizar_para_busqueda,
)


MEMORIA_ARCHIVO = "memoria.json"


VERSION_MEMORIA = 6


MAXIMO_LARGO_RECUERDO = 80


MAXIMO_TURNOS_CONVERSACION = 8


CONFIANZA_USUARIO = 1.0


CONFIANZA_INFERENCIA = 0.65


CONFIANZA_SISTEMA = 0.8


INICIOS_BASURA = (
    "que ",
    "cual ",
    "cuales ",
    "como ",
    "cuando ",
    "donde ",
    "olvida ",
    "cambia ",
    "ya no ",
    "historial",
    "salir",
    "ayuda",
)


def _crear_estructura_base() -> dict[str, Any]:

    return {
        "perfil": {
            "nombre": "",
            "fecha_nacimiento": "",
            "alias": "",
        },
        "usuario": {
            "gustos": {
                categoria: []
                for categoria in CATEGORIAS_GUSTOS_MEMORIA
            },
            "preferencias": {},
            "habilidades": [],
            "objetivos": [],
            "herramientas": {
                categoria: []
                for categoria in CATEGORIAS_HERRAMIENTAS_MEMORIA
            },
        },
        "proyectos": {},
        "aprendizaje": {
            categoria: []
            for categoria in CATEGORIAS_APRENDIZAJE_MEMORIA
        },
        "contexto": {
            "ultimo_comando": "",
            "ultimo_contexto": "",
        },
        "historial": [],
        "conversacion": [],
        "semantica": {
            "entidades": {},
            "relaciones": [],
        },
        "episodica": {
            "eventos": [],
        },
        "sistema": {
            "version_memoria": VERSION_MEMORIA,
        },
    }


def _asegurar_perfil(memoria: dict[str, Any]) -> None:

    base = _crear_estructura_base()["perfil"]
    perfil = _asegurar_diccionario(memoria, "perfil")

    for clave, valor in base.items():
        perfil.setdefault(clave, valor)


def _asegurar_usuario(memoria: dict[str, Any]) -> None:

    usuario = _asegurar_diccionario(memoria, "usuario")
    gustos = _asegurar_diccionario(usuario, "gustos")

    for categoria in CATEGORIAS_GUSTOS_MEMORIA:
        _asegurar_lista(gustos, categoria)

    _asegurar_diccionario(usuario, "preferencias")
    _asegurar_lista(usuario, "habilidades")
    _asegurar_lista(usuario, "objetivos")
    herramientas = _asegurar_diccionario(usuario, "herramientas")

    for categoria in CATEGORIAS_HERRAMIENTAS_MEMORIA:
        _asegurar_lista(herramientas, categoria)


def _asegurar_raiz(memoria: dict[str, Any]) -> None:

    base = _crear_estructura_base()

    _asegurar_diccionario(memoria, "proyectos")
    aprendizaje = _asegurar_diccionario(memoria, "aprendizaje")

    for categoria in CATEGORIAS_APRENDIZAJE_MEMORIA:
        _asegurar_lista(aprendizaje, categoria)

    contexto = _asegurar_diccionario(memoria, "contexto")

    for clave, valor in base["contexto"].items():
        contexto.setdefault(clave, valor)

    _asegurar_lista(memoria, "historial")
    conversacion = _asegurar_lista(memoria, "conversacion")
    _normalizar_conversacion(conversacion)
    semantica = _asegurar_diccionario(memoria, "semantica")
    _asegurar_diccionario(semantica, "entidades")
    _asegurar_lista(semantica, "relaciones")
    episodica = _asegurar_diccionario(memoria, "episodica")
    _asegurar_lista(episodica, "eventos")
    sistema = _asegurar_diccionario(memoria, "sistema")
    version_actual = sistema.get("version_memoria", 0)

    if not isinstance(version_actual, int) or version_actual < VERSION_MEMORIA:
        sistema["version_memoria"] = VERSION_MEMORIA


def _sincronizar_compatibilidad(memoria: dict[str, Any]) -> None:

    perfil = memoria.get("perfil", {})
    contexto = memoria.get("contexto", {})

    memoria["nombre"] = perfil.get("nombre", memoria.get("nombre", ""))
    memoria["fecha_nacimiento"] = perfil.get(
        "fecha_nacimiento",
        memoria.get("fecha_nacimiento", "")
    )
    memoria["ultimo_comando"] = contexto.get(
        "ultimo_comando",
        memoria.get("ultimo_comando", "")
    )
    memoria["ultimo_contexto"] = contexto.get(
        "ultimo_contexto",
        memoria.get("ultimo_contexto", "")
    )
    memoria.setdefault("frases_importantes", [])


def _asegurar_diccionario(
    datos: dict[str, Any],
    clave: str
) -> dict[str, Any]:

    valor = datos.get(clave)

    if isinstance(valor, dict):
        return valor

    if valor is not None:
        datos[f"{clave}_legacy"] = valor

    datos[clave] = {}
    return datos[clave]


def _asegurar_lista(
    datos: dict[str, Any],
    clave: str
) -> list[Any]:

    valor = datos.get(clave)

    if isinstance(valor, list):
        return valor

    if valor is None:
        datos[clave] = []
    else:
        datos[clave] = [valor]

    return datos[clave]


def _agregar_unico(lista: list[str], valor: str) -> None:

    valor = _limpiar_recuerdo(valor)

    if not valor:
        return

    valores_normalizados = {
        normalizar_para_busqueda(elemento)
        for elemento in lista
        if isinstance(elemento, str)
    }

    if normalizar_para_busqueda(valor) not in valores_normalizados:
        lista.append(valor)


def _normalizar_conversacion(conversacion: list[Any]) -> None:
    limpios = []

    for turno in conversacion:
        if not isinstance(turno, dict):
            continue

        usuario = _limpiar_texto_conversacion(turno.get("usuario", ""))
        orion = _limpiar_texto_conversacion(turno.get("orion", ""))

        if not usuario or not orion:
            continue

        normalizado = {
            "usuario": usuario,
            "orion": orion,
            "fecha": str(turno.get("fecha") or _fecha_iso()),
        }

        if not limpios or _clave_turno(limpios[-1]) != _clave_turno(normalizado):
            limpios.append(normalizado)

    conversacion[:] = limpios[-MAXIMO_TURNOS_CONVERSACION:]


def _limpiar_texto_conversacion(valor: Any) -> str:
    if not isinstance(valor, str):
        return ""

    valor = re.sub(r"\s+", " ", valor.strip())

    if not valor or len(valor) > 1200:
        return ""

    return valor


def _recortar_conversacion(conversacion: list[Any], limite: int) -> None:
    limite = max(0, int(limite))

    if len(conversacion) > limite:
        conversacion[:] = conversacion[-limite:]


def _clave_turno(turno: dict[str, Any]) -> tuple[str, str]:
    return (
        normalizar_para_busqueda(str(turno.get("usuario", ""))),
        normalizar_para_busqueda(str(turno.get("orion", ""))),
    )


def _es_episodio_valido(tipo: str, contenido: str) -> bool:
    tipos_validos = {
        "gusto",
        "aprendizaje",
        "objetivo",
        "proyecto",
        "correccion",
        "olvido",
        "herramienta",
    }

    return tipo in tipos_validos and bool(contenido)


def _normalizar_fuente(fuente: str) -> str:
    fuente_normalizada = normalizar_para_busqueda(fuente)

    if fuente_normalizada in {"usuario", "inferencia", "sistema"}:
        return fuente_normalizada

    return "sistema"


def _normalizar_confianza(confianza: Any) -> float:
    try:
        valor = float(confianza)
    except (TypeError, ValueError):
        return CONFIANZA_SISTEMA

    return max(0.0, min(1.0, valor))


def _fecha_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clave_recuerdo(valor: Any) -> str:
    return normalizar_para_busqueda(canonizar_entidad(str(valor)))


def _limpiar_recuerdo(valor: Any) -> str:
    if not isinstance(valor, str):
        return ""

    valor_limpio = canonizar_entidad(limpiar_valor(valor))
    valor_normalizado = normalizar_para_busqueda(valor_limpio)

    if not valor_limpio or len(valor_limpio) > MAXIMO_LARGO_RECUERDO:
        return ""

    if any(valor_normalizado.startswith(inicio) for inicio in INICIOS_BASURA):
        return ""

    return valor_limpio


def _id_memoria(tipo: str, categoria: str, contenido: str) -> str:
    identidad = "|".join((
        normalizar_para_busqueda(tipo),
        normalizar_para_busqueda(categoria),
        _clave_recuerdo(contenido),
    ))
    resumen = hashlib.sha256(identidad.encode("utf-8")).hexdigest()[:12]
    return f"mem-{resumen}"


def _formatear_lista(valores: list[Any]) -> str:
    limpios = [
        str(valor)
        for valor in valores
        if isinstance(valor, str) and valor.strip()
    ]

    return ", ".join(limpios)

