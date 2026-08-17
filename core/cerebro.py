from __future__ import annotations

import random
from typing import Any, Callable

from comandos.navegador import es_comando_navegador
from core.handlers.alias import procesar_alias
from core.handlers.aplicaciones import (
    confirmar_accion_pc,
    puede_manejar_aplicaciones,
    procesar_aplicaciones,
)
from core.handlers.configuracion import procesar_configuracion
from core.handlers.contratos import ResultadoCerebro
from core.handlers.ia import resolver_ia
from core.handlers.intencion import resolver_intencion
from core.ejecutor import ESTADO_REQUIERE_CONFIRMACION, EjecutorPlan
from core.tools import ejecutar_herramienta
from core.handlers.memoria import (
    confirmar_accion_memoria,
    procesar_accion_memoria,
    procesar_memoria,
    puede_manejar_accion_memoria,
)
from core.handlers.memoria_conversacional import (
    confirmar_memoria,
    es_confirmacion_afirmativa,
    es_confirmacion_negativa,
    procesar_memoria_conversacional,
)
from core.handlers.notas import (
    confirmar_eliminacion_nota,
    puede_manejar_notas,
    procesar_notas,
)
from core.handlers.registro import ayuda_comando_local_invalido
from core.handlers.skills import procesar_skills
from core.handlers.tareas import (
    confirmar_eliminar_tarea,
    puede_manejar_tareas,
    procesar_tareas,
)
from core.continuacion import CONTINUADOR, pasos_desde, serializar_pasos
from core.interprete import analizar
from core.intenciones import detectar_intencion
from core.planificador import planificar
from core.memoria import (
    actualizar_perfil,
    agregar_historial,
    aprender,
    guardar_contexto,
    guardar_memoria,
)
from core.personalidad import responder_personalidad


GuardarFunc = Callable[[], None]


def procesar(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    notas: list[Any] | None = None,
    alias: dict[str, str] | None = None,
    recordatorios: list[str] | None = None,
    guardar_notas: GuardarFunc | None = None,
    guardar_alias: GuardarFunc | None = None,
    guardar_config: GuardarFunc | None = None,
    archivo_notas: str | None = None,
) -> ResultadoCerebro:

    notas = notas if notas is not None else []
    alias = alias if alias is not None else {}
    recordatorios = recordatorios if recordatorios is not None else []

    CONTINUADOR.marcar_nuevo_comando()

    intencion = detectar_intencion(texto)

    resultado = ResultadoCerebro(
        texto=texto,
        intencion=intencion,
    )

    if _resolver_planificacion(texto, resultado, config):
        return resultado

    if _resolver_comandos_locales(
        texto,
        intencion,
        memoria,
        config,
        notas,
        alias,
        recordatorios,
        guardar_notas,
        guardar_alias,
        guardar_config,
        archivo_notas,
        resultado,
    ):
        return resultado

    conocimiento = _registrar_aprendizaje(texto, memoria)
    resultado.conocimiento = conocimiento

    if conocimiento is not None:
        resultado.accion = "aprendizaje"

        if conocimiento.tipo == "gusto":
            mensaje = (
                f"Entendido. Recordaré que te gusta "
                f"{conocimiento.valor} en {conocimiento.categoria}."
            )

        elif conocimiento.tipo == "aprendizaje":
            mensaje = (
                f"Entendido. Recordaré que estás aprendiendo "
                f"{conocimiento.valor} en {conocimiento.categoria}."
            )

        elif conocimiento.tipo == "objetivo":
            mensaje = (
                f"Objetivo guardado: {conocimiento.valor}."
            )

        else:
            mensaje = (
                f"Información guardada: {conocimiento.valor}."
            )

        resultado.respuesta = responder_personalidad(
            mensaje,
            config,
        )

        return resultado

    if _resolver_memoria_conversacional(texto, memoria, config, resultado):
        return resultado

    if resolver_ia(texto, memoria, config, resultado):
        return resultado

    resultado.respuesta = random.choice([
        "No entendí 🤔",
        "Explícame diferente 😄",
    ])

    resultado.accion = "desconocido"

    return resultado


def _resolver_planificacion(
    texto: str,
    resultado: ResultadoCerebro,
    config: dict[str, Any],
) -> bool:
    """Ruta interprete + planificador + ejecutor.

    Construye el plan y lo ejecuta EN ORDEN a traves de core/ejecutor
    (EjecutorPlan). Solo reclama frases que el interprete reconoce y
    cuyo plan es reconocido y resoluble; el resto continua con los
    handlers antiguos. La ejecucion usa ToolRegistry como unica via a
    las Tools y respeta la puerta de permisos (EjecutorAccionesPC) que
    vive dentro de cada Tool de acciones de PC.
    """
    analisis = analizar(texto)

    if not analisis:
        return False

    plan = planificar(analisis)

    if not (plan.reconocido and plan.resoluble):
        return False

    ejecucion = _EJECUTOR_PLAN.ejecutar(plan, config=config)

    resultado.intencion = "planificacion"
    resultado.accion = "ejecutar_plan"
    resultado.reconocido = True
    resultado.acciones = plan.pasos
    resultado.respuestas = tuple(
        paso_ejecucion.respuesta
        for paso_ejecucion in ejecucion.resultados
        if paso_ejecucion.respuesta
    )
    resultado.respuesta = resultado.respuesta_compuesta()

    if ejecucion.requiere_confirmacion and ejecucion.solicitud is not None:
        pendiente = ejecucion.paso_pendiente
        solicitud = dict(ejecucion.solicitud)
        solicitud["texto"] = texto

        if pendiente is not None:
            restantes = pasos_desde(plan, pendiente.paso.orden)
            solicitud["pasos_restantes"] = serializar_pasos(restantes)
            solicitud["respuestas_previas"] = [
                paso_resultado.respuesta
                for paso_resultado in ejecucion.resultados
                if paso_resultado.respuesta
                and paso_resultado.estado != ESTADO_REQUIERE_CONFIRMACION
            ]

        solicitud = CONTINUADOR.registrar_solicitud(solicitud)
        resultado.solicitud = solicitud
        resultado.solicitud_pendiente = solicitud
        resultado.respuesta = solicitud.get(
            "texto_confirmacion",
            resultado.respuesta,
        )

    resultado.debug = {
        "plan": {
            "reconocido": plan.reconocido,
            "resoluble": plan.resoluble,
            "pasos": len(plan.pasos),
        },
        "ejecucion": {
            "exito": ejecucion.exito,
            "ejecutados": len(ejecucion.pasos_ejecutados()),
            "fallidos": len(ejecucion.pasos_fallidos()),
            "bloqueados": len(ejecucion.pasos_bloqueados()),
            "omitidos": len(ejecucion.pasos_omitidos()),
            "requiere_confirmacion": ejecucion.requiere_confirmacion,
            "paso_pendiente": (
                ejecucion.paso_pendiente.paso.orden
                if ejecucion.paso_pendiente is not None
                else None
            ),
        },
    }
    return True


_EJECUTOR_PLAN = EjecutorPlan()


def completar_solicitud(
    solicitud: str | dict[str, Any],
    valor: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
) -> ResultadoCerebro:
    """Completa una solicitud que requiere datos adicionales del usuario."""
    valor = valor.strip()

    if not valor:
        return ResultadoCerebro(
            texto=valor,
            intencion=str(solicitud),
            accion="solicitud_invalida",
            respuesta="El valor no puede estar vacío.",
        )

    if isinstance(solicitud, dict):
        return _completar_solicitud_estructurada(
            solicitud,
            valor,
            memoria,
            config,
        )

    if solicitud == "nombre":
        actualizar_perfil(memoria, nombre=valor)
        guardar_memoria(memoria)
        return ResultadoCerebro(
            texto=valor,
            intencion="nombre",
            accion="actualizar_nombre",
            respuesta="Guardado 👍",
        )

    if solicitud == "fecha_nacimiento":
        actualizar_perfil(memoria, fecha_nacimiento=valor)
        guardar_memoria(memoria)
        return ResultadoCerebro(
            texto=valor,
            intencion="cumple",
            accion="actualizar_cumple",
            respuesta="Guardado 👍",
        )

    return ResultadoCerebro(
        texto=valor,
        intencion=str(solicitud),
        accion="solicitud_desconocida",
        respuesta="No pude completar esa solicitud.",
    )


def _completar_solicitud_estructurada(
    solicitud: dict[str, Any],
    valor: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
) -> ResultadoCerebro:
    tipo = str(solicitud.get("tipo", ""))

    if es_confirmacion_negativa(valor):
        return ResultadoCerebro(
            texto=valor,
            intencion=tipo,
            accion="confirmacion_cancelada",
            respuesta="Cancelado.",
        )

    if not es_confirmacion_afirmativa(valor):
        return ResultadoCerebro(
            texto=valor,
            intencion=tipo,
            accion="confirmacion_invalida",
            respuesta="No lo ejecute. Responde si, confirmar, adelante, no o cancelar.",
        )

    if tipo == "confirmar_memoria":
        return ResultadoCerebro(
            texto=valor,
            intencion=tipo,
            accion="guardar_memoria_conversacional",
            respuesta=confirmar_memoria(solicitud, memoria),
        )

    if tipo == "confirmar_tarea":
        return ResultadoCerebro(
            texto=valor,
            intencion=tipo,
            accion="eliminar_tarea",
            respuesta=confirmar_eliminar_tarea(solicitud),
        )

    if tipo == "confirmar_nota":
        return ResultadoCerebro(
            texto=valor,
            intencion=tipo,
            accion=str(solicitud.get("accion", "")),
            respuesta=confirmar_eliminacion_nota(solicitud),
        )

    if tipo == "confirmar_estado_memoria":
        return ResultadoCerebro(
            texto=valor,
            intencion=tipo,
            accion=str(solicitud.get("accion", "")),
            respuesta=confirmar_accion_memoria(solicitud, memoria),
        )

    if tipo == "confirmar_accion_pc":
        return ResultadoCerebro(
            texto=valor,
            intencion=tipo,
            accion=str(solicitud.get("accion", "")),
            respuesta=confirmar_accion_pc(solicitud, config),
        )

    return ResultadoCerebro(
        texto=valor,
        intencion=tipo,
        accion="solicitud_desconocida",
        respuesta="No pude completar esa solicitud.",
    )


def _registrar_aprendizaje(
    texto: str,
    memoria: dict[str, Any]
) -> Any | None:
    conocimiento = aprender(texto, memoria, guardar=False)

    if conocimiento is not None:
        agregar_historial(texto, memoria, guardar=False)
        guardar_contexto(texto, memoria, guardar=False)
        guardar_memoria(memoria)

    return conocimiento


def _resolver_comando_directo(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    notas: list[Any],
    alias: dict[str, str],
    recordatorios: list[str],
    guardar_notas: GuardarFunc | None,
    guardar_alias: GuardarFunc | None,
    guardar_config: GuardarFunc | None,
    archivo_notas: str | None,
    resultado: ResultadoCerebro,
) -> bool:
    del recordatorios

    if puede_manejar_accion_memoria(texto) and _aplicar_procesado(
        resultado,
        procesar_accion_memoria(texto, memoria),
    ):
        return True

    if puede_manejar_notas(texto) and _aplicar_procesado(
        resultado,
        procesar_notas(
            texto,
            notas,
            guardar_notas=guardar_notas,
            archivo_notas=archivo_notas,
        ),
    ):
        return True

    if _aplicar_procesado(
        resultado,
        procesar_configuracion(texto, config, guardar_config=guardar_config),
    ):
        return True

    if _aplicar_procesado(
        resultado,
        procesar_alias(texto, alias, config, guardar_alias=guardar_alias),
    ):
        return True

    if _aplicar_procesado(
        resultado,
        procesar_skills(texto),
    ):
        return True

    return False


def _resolver_comandos_locales(
    texto: str,
    intencion: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    notas: list[Any],
    alias: dict[str, str],
    recordatorios: list[str],
    guardar_notas: GuardarFunc | None,
    guardar_alias: GuardarFunc | None,
    guardar_config: GuardarFunc | None,
    archivo_notas: str | None,
    resultado: ResultadoCerebro,
) -> bool:
    if puede_manejar_aplicaciones(texto) and _resolver_aplicaciones(
        texto,
        config,
        resultado,
    ):
        return True

    if puede_manejar_tareas(texto) and _resolver_tareas(texto, resultado):
        return True

    if _resolver_comando_directo(
        texto,
        memoria,
        config,
        notas,
        alias,
        recordatorios,
        guardar_notas,
        guardar_alias,
        guardar_config,
        archivo_notas,
        resultado,
    ):
        return True

    if resolver_intencion(texto, intencion, memoria, config, resultado):
        return True

    if _resolver_consulta_memoria(texto, memoria, config, resultado):
        return True

    if es_comando_navegador(texto):
        resultado.intencion = "navegador"
        tool = ejecutar_herramienta("abrir_navegador", {"consulta": texto})
        if tool.exito:
            resultado.accion = "navegador"
        else:
            resultado.accion = "error_navegador"
            resultado.respuesta = "No pude abrir el navegador predeterminado."
        return True

    ayuda = ayuda_comando_local_invalido(texto)
    if ayuda:
        resultado.intencion = "comando_local_invalido"
        resultado.accion = "ayuda_comando_local"
        resultado.respuesta = ayuda
        return True

    return False


def _resolver_aplicaciones(
    texto: str,
    config: dict[str, Any],
    resultado: ResultadoCerebro,
) -> bool:
    if not puede_manejar_aplicaciones(texto):
        return False

    procesado, accion, respuesta, solicitud = procesar_aplicaciones(texto, config)

    if not procesado:
        return False

    resultado.accion = accion
    resultado.respuesta = respuesta
    resultado.solicitud_pendiente = solicitud
    resultado.solicitud = solicitud
    return True


def _resolver_tareas(
    texto: str,
    resultado: ResultadoCerebro,
) -> bool:
    if not puede_manejar_tareas(texto):
        return False

    procesado, accion, respuesta, solicitud = procesar_tareas(texto)

    if not procesado:
        return False

    resultado.accion = accion
    resultado.respuesta = respuesta
    resultado.solicitud_pendiente = solicitud
    resultado.solicitud = solicitud
    return True


def _resolver_memoria_conversacional(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    resultado: ResultadoCerebro,
) -> bool:
    procesado, accion, respuesta, solicitud = procesar_memoria_conversacional(
        texto,
        memoria,
        config,
    )

    if not procesado:
        return False

    resultado.accion = accion
    resultado.respuesta = responder_personalidad(respuesta, config)
    resultado.solicitud_pendiente = solicitud
    resultado.solicitud = solicitud
    return True


def _resolver_consulta_memoria(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
    resultado: ResultadoCerebro,
) -> bool:
    procesado, accion, respuesta = procesar_memoria(texto, memoria)

    if not procesado:
        return False

    resultado.accion = accion
    resultado.respuesta = responder_personalidad(respuesta, config)
    return True


def _aplicar_procesado(
    resultado: ResultadoCerebro,
    procesado: tuple[Any, ...],
) -> bool:
    fue_procesado, accion, respuesta, *resto = procesado

    if not fue_procesado:
        return False

    resultado.accion = accion
    resultado.respuesta = respuesta
    if resto:
        solicitud = resto[0]
        resultado.solicitud_pendiente = solicitud
        resultado.solicitud = solicitud
    return True
