"""Continuacion interactiva de confirmaciones de politica (Fase 9).

Cuando un plan se detiene en un paso CONFIRMAR, el cerebro expone una
solicitud con el paso pendiente y los pasos restantes. Este modulo
permite continuar (o cancelar) esa solicitud reutilizando la MISMA ruta
de ejecucion: ToolRegistry -> EjecutorPlan -> politica -> parametros ->
EjecutorAccionesPC. main.py solo presenta el texto y traduce la
respuesta del usuario a un booleano; el resto vive aqui.

Protecciones:
- Una solicitud confirmada/cancelada queda consumida y no puede
  ejecutarse dos veces.
- Una solicitud queda obsoleta cuando ORION procesa otro comando.
"""

from __future__ import annotations

from typing import Any

from core.ejecutor import EjecutorPlan
from core.ejecutor.contratos import ResultadoEjecucion
from core.conocimiento import normalizar_para_busqueda
from core.handlers.contratos import ResultadoCerebro
from core.interprete.contratos import Entidad
from core.planificador.contratos import ESTADO_PLANIFICABLE, Paso, Plan

SOLICITUD_TIPO = "confirmar_politica"

AFIRMACIONES = {"si", "s", "confirmar", "adelante", "ok", "vale", "claro"}
NEGACIONES = {"no", "n", "cancelar", "cancela", "detener", "deten"}


def es_afirmacion(texto: str) -> bool:
    return normalizar_para_busqueda(texto) in AFIRMACIONES


def es_negacion(texto: str) -> bool:
    return normalizar_para_busqueda(texto) in NEGACIONES


def pasos_desde(plan: Plan, orden: int) -> list[Paso]:
    """Pasos de `plan` desde el que tiene `orden` (inclusive)."""
    for indice, paso in enumerate(plan.pasos):
        if paso.orden == orden:
            return list(plan.pasos[indice:])
    return []


def serializar_pasos(pasos: list[Paso]) -> list[dict[str, Any]]:
    return [_paso_como_dict(paso) for paso in pasos]


def _paso_como_dict(paso: Paso) -> dict[str, Any]:
    entidad = paso.entidad
    return {
        "orden": paso.orden,
        "verbo": paso.verbo,
        "entidad": (
            {
                "tipo": entidad.tipo,
                "valor": entidad.valor,
                "normalizado": entidad.normalizado,
            }
            if entidad is not None
            else None
        ),
        "tool": paso.tool,
        "parametros": paso.parametros,
        "estado": paso.estado,
        "motivo": paso.motivo,
        "texto": paso.texto,
    }


def _paso_desde_dict(paso_dict: dict[str, Any]) -> Paso:
    entidad_dict = paso_dict.get("entidad")
    entidad = None
    if entidad_dict:
        entidad = Entidad(
            tipo=str(entidad_dict.get("tipo", "objeto")),
            valor=str(entidad_dict.get("valor", "")),
            normalizado=str(entidad_dict.get("normalizado", "")),
        )
    return Paso(
        orden=int(paso_dict.get("orden", 0)),
        verbo=str(paso_dict.get("verbo", "")),
        entidad=entidad,
        tool=paso_dict.get("tool"),
        parametros=dict(paso_dict.get("parametros", {})),
        estado=str(paso_dict.get("estado", ESTADO_PLANIFICABLE)),
        motivo=str(paso_dict.get("motivo", "")),
        texto=str(paso_dict.get("texto", "")),
    )


class ContinuadorConfirmaciones:
    """Encapsula el estado y la logica de una confirmacion pendiente."""

    def __init__(self, ejecutor: EjecutorPlan | None = None) -> None:
        self._ejecutor = ejecutor or EjecutorPlan()
        self._activa: dict[str, Any] | None = None
        self._contador = 0

    def reset(self) -> None:
        self._activa = None
        self._contador = 0

    def marcar_nuevo_comando(self) -> None:
        """Invalida la solicitud activa cuando se procesa otro comando."""
        self._contador += 1
        self._activa = None

    def registrar_solicitud(self, solicitud: dict[str, Any]) -> dict[str, Any]:
        """Registra una solicitud nueva y la devuelve como solicitud activa."""
        self._contador += 1
        solicitud = dict(solicitud)
        solicitud["_comando"] = self._contador
        solicitud["_consumida"] = False
        self._activa = solicitud
        return solicitud

    def continuar(
        self,
        solicitud: dict[str, Any],
        confirmar: bool,
        config: dict[str, Any] | None = None,
    ) -> ResultadoCerebro:
        """Continua (o cancela) una solicitud pendiente de confirmacion."""
        error = self._validar(solicitud)
        if error is not None:
            return error

        solicitud["_consumida"] = True
        if self._activa is not None:
            self._activa["_consumida"] = True
        self._activa = None

        if not confirmar:
            return _resultado_rechazo(
                "confirmacion_cancelada",
                "Cancelado.",
                texto=str(solicitud.get("texto", "")),
                intencion=str(solicitud.get("tipo", SOLICITUD_TIPO)),
            )

        return self._ejecutar_pendiente(solicitud, config)

    def _validar(
        self,
        solicitud: dict[str, Any],
    ) -> ResultadoCerebro | None:
        if not isinstance(solicitud, dict) or solicitud.get("tipo") != SOLICITUD_TIPO:
            return _resultado_rechazo(
                "solicitud_invalida",
                "No pude completar esa solicitud.",
                texto=str(solicitud.get("texto", "")),
                intencion=str(solicitud.get("tipo", "")),
            )

        if solicitud.get("_consumida"):
            return _resultado_rechazo(
                "solicitud_consumida",
                "Esa solicitud ya fue respondida.",
                texto=str(solicitud.get("texto", "")),
                intencion=SOLICITUD_TIPO,
            )

        if self._activa is None or solicitud.get("_comando") != self._activa.get(
            "_comando"
        ):
            return _resultado_rechazo(
                "solicitud_obsoleta",
                "Esa solicitud ya no esta vigente.",
                texto=str(solicitud.get("texto", "")),
                intencion=SOLICITUD_TIPO,
            )

        return None

    def _ejecutar_pendiente(
        self,
        solicitud: dict[str, Any],
        config: dict[str, Any] | None,
    ) -> ResultadoCerebro:
        pasos = [
            _paso_desde_dict(paso)
            for paso in solicitud.get("pasos_restantes", [])
        ]

        if not pasos:
            return _resultado_rechazo(
                "solicitud_incompleta",
                "No pude completar esa solicitud.",
                texto=str(solicitud.get("texto", "")),
                intencion=SOLICITUD_TIPO,
            )

        previas = [respuesta for respuesta in solicitud.get("respuestas_previas", []) if respuesta]
        texto = str(solicitud.get("texto", ""))
        subplan = Plan(
            texto_original=texto,
            pasos=tuple(pasos),
            reconocido=True,
            resoluble=True,
        )

        autorizado = {pasos[0].orden}
        ejecucion = self._ejecutor.ejecutar(
            subplan,
            config=config,
            autorizado=autorizado,
        )

        resultado = ResultadoCerebro(
            texto=texto,
            intencion="planificacion",
            accion="ejecutar_plan",
            reconocido=True,
            acciones=tuple(pasos),
        )

        if ejecucion.requiere_confirmacion and ejecucion.paso_pendiente is not None:
            nueva = self._registrar_pendiente(ejecucion, previas)
            resultado.solicitud = nueva
            resultado.solicitud_pendiente = nueva
            resultado.respuesta = nueva.get(
                "texto_confirmacion",
                "Se requiere confirmacion para continuar.",
            )
        else:
            resultado.respuestas = tuple(previas) + tuple(
                paso_resultado.respuesta
                for paso_resultado in ejecucion.resultados
                if paso_resultado.respuesta
            )
            resultado.respuesta = resultado.respuesta_compuesta()

        resultado.debug = {
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
                "continuacion": True,
            },
        }
        return resultado

    def _registrar_pendiente(
        self,
        ejecucion: ResultadoEjecucion,
        previas: list[str],
    ) -> dict[str, Any]:
        pendiente = ejecucion.paso_pendiente
        restantes = pasos_desde(ejecucion.plan, pendiente.paso.orden)

        previas_actualizadas = previas + [
            paso_resultado.respuesta
            for paso_resultado in ejecucion.resultados
            if paso_resultado.respuesta
            and paso_resultado is not pendiente
        ]

        nueva = dict(ejecucion.solicitud or {})
        nueva["texto"] = str(ejecucion.plan.texto_original)
        nueva["pasos_restantes"] = serializar_pasos(restantes)
        nueva["respuestas_previas"] = previas_actualizadas
        return self.registrar_solicitud(nueva)


def _resultado_rechazo(
    accion: str,
    respuesta: str,
    texto: str = "",
    intencion: str = SOLICITUD_TIPO,
) -> ResultadoCerebro:
    return ResultadoCerebro(
        texto=texto,
        intencion=intencion,
        accion=accion,
        respuesta=respuesta,
    )


CONTINUADOR = ContinuadorConfirmaciones()


def continuar_solicitud(
    solicitud: dict[str, Any],
    confirmar: bool,
    config: dict[str, Any] | None = None,
) -> ResultadoCerebro:
    """Continua (o cancela) la solicitud pendiente global."""
    return CONTINUADOR.continuar(solicitud, confirmar, config)
