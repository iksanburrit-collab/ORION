from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.conocimiento import (
    CATEGORIAS_APRENDIZAJE_MEMORIA,
    CATEGORIAS_GUSTOS_MEMORIA,
    ConocimientoDetectado,
    detectar_conocimiento,
)
from utilidades.archivos import guardar_json


MEMORIA_ARCHIVO = "memoria.json"
VERSION_MEMORIA = 3


def inicializar_memoria(memoria: dict[str, Any] | None) -> dict[str, Any]:

    if not isinstance(memoria, dict):
        memoria = {}

    _asegurar_perfil(memoria)
    _asegurar_usuario(memoria)
    _asegurar_raiz(memoria)
    _migrar_memoria_legacy(memoria)
    _sincronizar_compatibilidad(memoria)

    return memoria


def guardar_memoria(
    memoria: dict[str, Any],
    archivo: str = MEMORIA_ARCHIVO
) -> None:

    guardar_json(archivo, memoria)


def aprender(
    texto: str,
    memoria: dict[str, Any],
    guardar: bool = True
) -> ConocimientoDetectado | None:

    conocimiento = detectar_conocimiento(texto)

    if not conocimiento:
        return None

    if conocimiento.tipo == "gusto":
        registrar_gusto(
            memoria,
            conocimiento.categoria,
            conocimiento.valor
        )

        if conocimiento.clave_preferencia:
            preferencias = memoria["usuario"]["preferencias"]
            preferencias.setdefault(
                f"{conocimiento.clave_preferencia}_favorito",
                conocimiento.valor
            )

    elif conocimiento.tipo == "aprendizaje":
        registrar_aprendizaje(
            memoria,
            conocimiento.categoria,
            conocimiento.valor
        )

    memoria["contexto"]["ultimo_aprendizaje"] = {
        "tipo": conocimiento.tipo,
        "categoria": conocimiento.categoria,
        "valor": conocimiento.valor,
    }

    if guardar:
        guardar_memoria(memoria)

    return conocimiento


def registrar_gusto(
    memoria: dict[str, Any],
    categoria: str,
    valor: str
) -> None:

    gustos = memoria["usuario"]["gustos"]

    if categoria not in gustos:
        gustos[categoria] = []

    _agregar_unico(gustos[categoria], valor)


def registrar_aprendizaje(
    memoria: dict[str, Any],
    categoria: str,
    valor: str
) -> None:

    aprendizaje = memoria["aprendizaje"]

    if categoria not in aprendizaje:
        aprendizaje[categoria] = []

    if isinstance(aprendizaje[categoria], list):
        _agregar_unico(aprendizaje[categoria], valor)


def guardar_contexto(
    comando: str,
    memoria: dict[str, Any],
    contexto: str = "",
    guardar: bool = True
) -> None:

    memoria["contexto"]["ultimo_comando"] = comando
    memoria["contexto"]["ultimo_contexto"] = contexto
    _sincronizar_compatibilidad(memoria)

    if guardar:
        guardar_memoria(memoria)


def agregar_historial(
    comando: str,
    memoria: dict[str, Any],
    limite: int = 20,
    guardar: bool = True
) -> None:

    memoria["historial"].append(comando)

    if len(memoria["historial"]) > limite:
        memoria["historial"].pop(0)

    if guardar:
        guardar_memoria(memoria)


def actualizar_perfil(
    memoria: dict[str, Any],
    nombre: str | None = None,
    fecha_nacimiento: str | None = None,
    alias: str | None = None
) -> None:

    perfil = memoria["perfil"]

    if nombre is not None:
        perfil["nombre"] = nombre

    if fecha_nacimiento is not None:
        perfil["fecha_nacimiento"] = fecha_nacimiento

    if alias is not None:
        perfil["alias"] = alias

    _sincronizar_compatibilidad(memoria)


def obtener_nombre(memoria: dict[str, Any]) -> str:

    return memoria.get("perfil", {}).get("nombre", "")


def obtener_fecha_nacimiento(memoria: dict[str, Any]) -> str:

    return memoria.get("perfil", {}).get("fecha_nacimiento", "")


def obtener_ultimo_comando(memoria: dict[str, Any]) -> str:

    return memoria.get("contexto", {}).get("ultimo_comando", "")


def obtener_ultimo_gusto(memoria: dict[str, Any]) -> str:

    contexto = memoria.get("contexto", {})
    ultimo_aprendizaje = contexto.get("ultimo_aprendizaje", {})

    if ultimo_aprendizaje.get("tipo") == "gusto":
        return _formatear_gusto_recordado(
            ultimo_aprendizaje.get("categoria", "otros"),
            ultimo_aprendizaje.get("valor", "")
        )

    gustos = memoria.get("usuario", {}).get("gustos", {})

    for categoria, valores in reversed(list(gustos.items())):
        if valores:
            return _formatear_gusto_recordado(categoria, valores[-1])

    return ""


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
    sistema = _asegurar_diccionario(memoria, "sistema")
    version_actual = sistema.get("version_memoria", 0)

    if not isinstance(version_actual, int) or version_actual < VERSION_MEMORIA:
        sistema["version_memoria"] = VERSION_MEMORIA


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

    if not valor:
        return

    valores_normalizados = {
        elemento.strip().lower()
        for elemento in lista
        if isinstance(elemento, str)
    }

    if valor.strip().lower() not in valores_normalizados:
        lista.append(valor)


def _formatear_gusto_recordado(categoria: str, valor: str) -> str:

    if not valor:
        return ""

    return f"{categoria}: {valor}"
