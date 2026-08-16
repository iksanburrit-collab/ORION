from __future__ import annotations

from typing import Any

from core.conocimiento import (
    ConocimientoDetectado,
    clasificar_aprendizaje,
    clasificar_gusto,
    detectar_conocimiento,
    inferir_relaciones_semanticas,
)
from core.memoria.episodios import (
    _buscar_id_memoria_activa,
    olvidar_memoria,
    registrar_episodio,
)
from core.memoria.estructura import (
    CONFIANZA_USUARIO,
    MAXIMO_TURNOS_CONVERSACION,
    _agregar_unico,
    _asegurar_lista,
    _clave_turno,
    _fecha_iso,
    _limpiar_recuerdo,
    _limpiar_texto_conversacion,
    _recortar_conversacion,
    _sincronizar_compatibilidad,
    _formatear_lista,
)
from utilidades.archivos import guardar_json
from utilidades.rutas import ruta_memoria


def guardar_memoria(
    memoria: dict[str, Any],
    archivo: str | None = None,
) -> None:

    guardar_json(archivo or ruta_memoria(), memoria)


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
    memoria_id = _buscar_id_memoria_activa(
        memoria,
        "gusto",
        [valor, valor_canonico],
        [categoria, "otros"],
    )
    return olvidar_memoria(memoria, memoria_id) if memoria_id else False


def olvidar_aprendizaje(memoria: dict[str, Any], valor: str) -> bool:
    categoria, valor_canonico = clasificar_aprendizaje(valor)
    memoria_id = _buscar_id_memoria_activa(
        memoria,
        "aprendizaje",
        [valor, valor_canonico],
        [categoria, "otros"],
    )
    return olvidar_memoria(memoria, memoria_id) if memoria_id else False


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


def _formatear_mapa_listas(datos: dict[str, Any]) -> str:
    partes = []

    for categoria, valores in datos.items():
        if not isinstance(valores, list) or not valores:
            continue

        lista = _formatear_lista(valores)

        if lista:
            partes.append(f"{categoria}: {lista}")

    return "; ".join(partes)


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

