from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any

from core.conocimiento import (
    CATEGORIAS_APRENDIZAJE_MEMORIA,
    CATEGORIAS_GUSTOS_MEMORIA,
    CATEGORIAS_HERRAMIENTAS_MEMORIA,
    ConocimientoDetectado,
    canonizar_entidad,
    clasificar_aprendizaje,
    clasificar_gusto,
    detectar_conocimiento,
    inferir_relaciones_semanticas,
    limpiar_valor,
    normalizar_para_busqueda,
)
from utilidades.archivos import guardar_json


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


def inicializar_memoria(memoria: dict[str, Any] | None) -> dict[str, Any]:

    if not isinstance(memoria, dict):
        memoria = {}

    _asegurar_perfil(memoria)
    _asegurar_usuario(memoria)
    _asegurar_raiz(memoria)
    _migrar_memoria_legacy(memoria)
    _limpiar_memoria_funcional(memoria)
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
    guardar: bool = True,
    fuente: str = "usuario",
    confianza: float = CONFIANZA_USUARIO,
) -> ConocimientoDetectado | None:

    conocimiento = detectar_conocimiento(texto)

    if not conocimiento:
        return None

    if conocimiento.tipo == "gusto":
        registrar_gusto(
            memoria,
            conocimiento.categoria,
            conocimiento.valor,
            fuente=fuente,
            confianza=min(confianza, conocimiento.confianza),
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
            conocimiento.valor,
            fuente=fuente,
            confianza=confianza,
        )
    elif conocimiento.tipo == "objetivo":
        registrar_objetivo(
            memoria,
            conocimiento.valor,
            fuente=fuente,
            confianza=confianza,
        )
    elif conocimiento.tipo == "herramienta":
        registrar_herramienta(
            memoria,
            conocimiento.categoria,
            conocimiento.valor,
            fuente=fuente,
            confianza=confianza,
        )

    registrar_conocimiento_semantico(memoria, conocimiento)

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
    valor: str,
    fuente: str = "usuario",
    confianza: float = CONFIANZA_USUARIO,
) -> None:

    valor = _limpiar_recuerdo(valor)
    clasificacion = clasificar_gusto(valor)

    if categoria == "otros" and clasificacion.categoria != "otros":
        categoria = clasificacion.categoria

    if not valor:
        return

    gustos = memoria["usuario"]["gustos"]

    if categoria not in gustos:
        gustos[categoria] = []

    _agregar_unico(gustos[categoria], valor)
    registrar_episodio(
        memoria,
        "gusto",
        valor,
        categoria=categoria,
        fuente=fuente,
        confianza=confianza,
    )


def registrar_aprendizaje(
    memoria: dict[str, Any],
    categoria: str,
    valor: str,
    fuente: str = "usuario",
    confianza: float = CONFIANZA_USUARIO,
) -> None:

    valor = _limpiar_recuerdo(valor)

    if not valor:
        return

    aprendizaje = memoria["aprendizaje"]

    if categoria not in aprendizaje:
        aprendizaje[categoria] = []

    if isinstance(aprendizaje[categoria], list):
        _agregar_unico(aprendizaje[categoria], valor)
        registrar_episodio(
            memoria,
            "aprendizaje",
            valor,
            categoria=categoria,
            fuente=fuente,
            confianza=confianza,
        )


def registrar_objetivo(
    memoria: dict[str, Any],
    valor: str,
    fuente: str = "usuario",
    confianza: float = CONFIANZA_USUARIO,
) -> None:

    valor = _limpiar_recuerdo(valor)

    if not valor:
        return

    _agregar_unico(memoria["usuario"]["objetivos"], valor)
    registrar_episodio(
        memoria,
        "objetivo",
        valor,
        categoria="otros",
        fuente=fuente,
        confianza=confianza,
    )


def registrar_herramienta(
    memoria: dict[str, Any],
    categoria: str,
    valor: str,
    fuente: str = "usuario",
    confianza: float = CONFIANZA_USUARIO,
) -> None:

    valor = _limpiar_recuerdo(valor)

    if not valor:
        return

    herramientas = memoria["usuario"]["herramientas"]

    if categoria not in herramientas:
        categoria = "otros"

    _agregar_unico(herramientas[categoria], valor)
    registrar_episodio(
        memoria,
        "herramienta",
        valor,
        categoria=categoria,
        fuente=fuente,
        confianza=confianza,
    )


def registrar_turno_conversacion(
    memoria: dict[str, Any],
    mensaje_usuario: str,
    respuesta_orion: str,
    limite: int = MAXIMO_TURNOS_CONVERSACION,
    fecha: str | None = None,
) -> None:
    mensaje_usuario = _limpiar_texto_conversacion(mensaje_usuario)
    respuesta_orion = _limpiar_texto_conversacion(respuesta_orion)

    if (
        not mensaje_usuario
        or not respuesta_orion
        or respuesta_orion.startswith("No pude usar Ollama:")
    ):
        return

    conversacion = _asegurar_lista(memoria, "conversacion")
    turno = {
        "usuario": mensaje_usuario,
        "orion": respuesta_orion,
        "fecha": fecha or _fecha_iso(),
    }

    if conversacion and _clave_turno(conversacion[-1]) == _clave_turno(turno):
        return

    conversacion.append(turno)
    _recortar_conversacion(conversacion, limite)


def obtener_historial_conversacion(
    memoria: dict[str, Any],
    limite: int = MAXIMO_TURNOS_CONVERSACION,
) -> list[dict[str, str]]:
    conversacion = memoria.get("conversacion", [])

    if not isinstance(conversacion, list) or limite <= 0:
        return []

    mensajes = []

    for turno in conversacion[-limite:]:
        if not isinstance(turno, dict):
            continue

        usuario = _limpiar_texto_conversacion(turno.get("usuario", ""))
        orion = _limpiar_texto_conversacion(turno.get("orion", ""))

        if usuario and orion:
            mensajes.append({"role": "user", "content": usuario})
            mensajes.append({"role": "assistant", "content": orion})

    return mensajes


def registrar_conocimiento_semantico(
    memoria: dict[str, Any],
    conocimiento: ConocimientoDetectado
) -> None:

    semantica = memoria["semantica"]
    entidades = semantica["entidades"]
    entidad = entidades.setdefault(
        conocimiento.valor,
        {
            "nombre": conocimiento.valor,
            "tipos": [],
            "categorias": [],
            "fuentes": [],
        }
    )

    _agregar_unico(entidad["tipos"], conocimiento.tipo)
    _agregar_unico(entidad["categorias"], conocimiento.categoria)
    _agregar_unico(entidad["fuentes"], "aprendizaje_usuario")

    relaciones = inferir_relaciones_semanticas(
        conocimiento.valor,
        conocimiento.categoria,
        conocimiento.tipo
    )

    for relacion in relaciones:
        _agregar_relacion_unica(semantica["relaciones"], relacion)


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


def consultar_resumen_personal(memoria: dict[str, Any]) -> str:
    partes = []
    perfil = memoria.get("perfil", {})
    nombre = perfil.get("nombre", "")

    if nombre:
        partes.append(f"Tu nombre: {nombre}")

    gustos = _formatear_mapa_listas(
        memoria.get("usuario", {}).get("gustos", {})
    )
    aprendizaje = _formatear_mapa_listas(memoria.get("aprendizaje", {}))
    objetivos = _formatear_lista(
        memoria.get("usuario", {}).get("objetivos", [])
    )
    proyectos = consultar_proyectos(memoria)

    if gustos:
        partes.append(f"Gustos: {gustos}")

    if aprendizaje:
        partes.append(f"Aprendizaje: {aprendizaje}")

    if objetivos:
        partes.append(f"Objetivos: {objetivos}")

    if proyectos != "No tengo proyectos guardados":
        partes.append(f"Proyectos: {proyectos}")

    if not partes:
        return "Todavia no se mucho de ti"

    return "\n".join(partes)


def consultar_gustos(memoria: dict[str, Any], categoria: str) -> str:
    gustos = memoria.get("usuario", {}).get("gustos", {})
    valores = gustos.get(categoria, [])
    lista = _formatear_lista(valores)

    if lista:
        return lista

    return f"No tengo {categoria} guardados"


def consultar_aprendizaje(memoria: dict[str, Any]) -> str:
    aprendizaje = _formatear_mapa_listas(memoria.get("aprendizaje", {}))

    if aprendizaje:
        return aprendizaje

    return "No tengo aprendizajes guardados"


def consultar_objetivos(memoria: dict[str, Any]) -> str:
    objetivos = _formatear_lista(
        memoria.get("usuario", {}).get("objetivos", [])
    )

    if objetivos:
        return objetivos

    return "No tengo objetivos guardados"


def consultar_proyectos(memoria: dict[str, Any]) -> str:
    proyectos = memoria.get("proyectos", {})

    if isinstance(proyectos, dict) and proyectos:
        return ", ".join(str(nombre) for nombre in proyectos)

    if isinstance(proyectos, list) and proyectos:
        return _formatear_lista(proyectos)

    return "No tengo proyectos guardados"


def olvidar_gusto(memoria: dict[str, Any], valor: str) -> bool:
    clasificacion = clasificar_gusto(valor)
    categoria = clasificacion.categoria
    valor_canonico = clasificacion.valor
    candidatos = [valor, valor_canonico]
    gustos = memoria.get("usuario", {}).get("gustos", {})
    eliminado = False

    categorias = [categoria] if categoria in gustos else list(gustos)

    if categoria != "otros":
        categorias.append("otros")

    for categoria_actual in dict.fromkeys(categorias):
        valores = gustos.get(categoria_actual)

        if isinstance(valores, list):
            eliminado = _eliminar_de_lista(valores, candidatos) or eliminado

    _olvidar_preferencias(memoria, candidatos)
    _olvidar_entidades(memoria, candidatos)

    if eliminado:
        registrar_episodio(
            memoria,
            "olvido",
            valor,
            categoria=categoria,
            fuente="usuario",
            confianza=CONFIANZA_USUARIO,
        )

    return eliminado


def olvidar_aprendizaje(memoria: dict[str, Any], valor: str) -> bool:
    categoria, valor_canonico = clasificar_aprendizaje(valor)
    candidatos = [valor, valor_canonico]
    aprendizaje = memoria.get("aprendizaje", {})
    eliminado = False

    categorias = [categoria] if categoria in aprendizaje else list(aprendizaje)

    if categoria != "otros":
        categorias.append("otros")

    for categoria_actual in dict.fromkeys(categorias):
        valores = aprendizaje.get(categoria_actual)

        if isinstance(valores, list):
            eliminado = _eliminar_de_lista(valores, candidatos) or eliminado

    _olvidar_entidades(memoria, candidatos)

    if eliminado:
        registrar_episodio(
            memoria,
            "olvido",
            valor,
            categoria=categoria,
            fuente="usuario",
            confianza=CONFIANZA_USUARIO,
        )

    return eliminado


def cambiar_objetivo(memoria: dict[str, Any], valor: str) -> bool:
    valor_limpio = _limpiar_recuerdo(valor)

    if not valor_limpio:
        return False

    memoria["usuario"]["objetivos"] = [valor_limpio]
    registrar_episodio(
        memoria,
        "correccion",
        f"Objetivo cambiado a {valor_limpio}",
        categoria="objetivo",
        fuente="usuario",
        confianza=CONFIANZA_USUARIO,
    )
    return True


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
        "tipo": tipo,
        "contenido": contenido_limpio,
        "categoria": categoria or "otros",
        "fecha": fecha or _fecha_iso(),
        "fuente": _normalizar_fuente(fuente),
        "confianza": _normalizar_confianza(confianza),
    }
    episodica = _asegurar_diccionario(memoria, "episodica")
    eventos = _asegurar_lista(episodica, "eventos")

    if _episodio_duplicado(eventos, episodio):
        return False

    eventos.append(episodio)
    return True


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


def _normalizar_episodios(eventos: list[Any]) -> None:
    limpios = []

    for evento in eventos:
        if not isinstance(evento, dict):
            continue

        contenido = _limpiar_recuerdo(evento.get("contenido", ""))
        tipo = str(evento.get("tipo", "")).strip().lower()

        if not _es_episodio_valido(tipo, contenido):
            continue

        normalizado = {
            "tipo": tipo,
            "contenido": contenido,
            "categoria": str(evento.get("categoria", "otros") or "otros"),
            "fecha": str(evento.get("fecha") or _fecha_iso()),
            "fuente": _normalizar_fuente(str(evento.get("fuente", "usuario"))),
            "confianza": _normalizar_confianza(
                evento.get("confianza", CONFIANZA_USUARIO)
            ),
        }

        if not _episodio_duplicado(limpios, normalizado):
            limpios.append(normalizado)

    eventos[:] = limpios


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


def _formatear_mapa_listas(datos: dict[str, Any]) -> str:
    partes = []

    for categoria, valores in datos.items():
        if not isinstance(valores, list) or not valores:
            continue

        lista = _formatear_lista(valores)

        if lista:
            partes.append(f"{categoria}: {lista}")

    return "; ".join(partes)


def _formatear_lista(valores: list[Any]) -> str:
    limpios = [
        str(valor)
        for valor in valores
        if isinstance(valor, str) and valor.strip()
    ]

    return ", ".join(limpios)


def _agregar_relacion_unica(
    relaciones: list[dict[str, str]],
    relacion: dict[str, str]
) -> None:

    clave = (
        relacion.get("origen", "").strip().lower(),
        relacion.get("relacion", "").strip().lower(),
        relacion.get("destino", "").strip().lower(),
    )

    for existente in relaciones:
        if not isinstance(existente, dict):
            continue

        clave_existente = (
            str(existente.get("origen", "")).strip().lower(),
            str(existente.get("relacion", "")).strip().lower(),
            str(existente.get("destino", "")).strip().lower(),
        )

        if clave_existente == clave:
            return

    relaciones.append(relacion)


def _formatear_gusto_recordado(categoria: str, valor: str) -> str:

    if not valor:
        return ""

    return f"{categoria}: {valor}"
