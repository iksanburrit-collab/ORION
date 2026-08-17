from __future__ import annotations

from copy import deepcopy
import sys
from typing import Any

from core.cerebro import completar_solicitud, procesar
from core.continuacion import continuar_solicitud, es_afirmacion, es_negacion
from core.memoria import guardar_memoria, inicializar_memoria
from servicios.calendario.legacy import migrar_recordatorios_legacy
from servicios.notas import RepositorioNotas
from utilidades.archivos import asegurar_json, cargar_json, guardar_json
from utilidades.configuracion import cargar_configuracion
from utilidades.entorno import cargar_entorno
from utilidades.rutas import (
    ruta_alias,
    ruta_configuracion,
    ruta_memoria,
    ruta_notas,
    ruta_recordatorios,
)
from utilidades.texto import normalizar_comando


def inicializar_orion() -> dict[str, Any]:
    cargar_entorno()
    resultado_memoria = cargar_json(ruta_memoria(), {})
    memoria_antes = deepcopy(resultado_memoria.datos)
    memoria = inicializar_memoria(resultado_memoria.datos)
    repositorio_notas = RepositorioNotas(ruta_notas())
    resultado_recordatorios = cargar_json(ruta_recordatorios(), [])
    recordatorios = (
        resultado_recordatorios.datos
        if isinstance(resultado_recordatorios.datos, list)
        else []
    )
    alias = asegurar_json(ruta_alias(), {})
    config = cargar_configuracion(ruta_configuracion())

    if resultado_memoria.error is None and memoria != memoria_antes:
        guardar_memoria(memoria, ruta_memoria())

    def guardar_recordatorios() -> None:
        guardar_json(ruta_recordatorios(), recordatorios)

    if resultado_recordatorios.error is None:
        migrar_recordatorios_legacy(
            recordatorios,
            guardar_recordatorios=guardar_recordatorios,
        )

    return {
        "memoria": memoria,
        "repositorio_notas": repositorio_notas,
        "notas": repositorio_notas.datos,
        "recordatorios": recordatorios,
        "alias": alias,
        "config": config,
    }


def mostrar_debug_ia(debug: dict[str, Any] | None) -> None:
    if not debug:
        return

    tiempo = debug.get("tiempo_respuesta")
    if tiempo is not None:
        print("Tiempo:")
        print(f"{tiempo:.2f} s")


_USO = """Uso:
  orion [--help]

Opciones:
  -h, --help  Muestra esta ayuda y sale.
"""


def _atender_solicitudes(
    resultado: Any,
    memoria: dict[str, Any],
    config: dict[str, Any],
) -> bool:
    """Presenta y completa las solicitudes pendientes del resultado.

    Devuelve True si habia una solicitud que atender. main.py sigue
    siendo un CLI delgado: la logica de continuacion de confirmaciones
    de politica vive en core/continuacion, y las solicitudes antiguas
    (confirmar_accion_pc, confirmar_memoria, etc.) se completan con el
    flujo previo (completar_solicitud).
    """
    atendidas = False

    while True:
        solicitud = resultado.solicitud_pendiente or resultado.solicitud
        if not solicitud:
            break

        atendidas = True

        if isinstance(solicitud, dict) and solicitud.get("tipo") == "confirmar_politica":
            resultado = _atender_confirmacion_politica(solicitud, config)
            continue

        resultado = _atender_solicitud_legacy(solicitud, memoria, config)

    if atendidas and resultado.respuesta:
        print(resultado.respuesta)

    return atendidas


def _atender_confirmacion_politica(
    solicitud: dict[str, Any],
    config: dict[str, Any],
) -> Any:
    while True:
        texto = solicitud.get(
            "texto_confirmacion",
            "Se requiere confirmación para ejecutar la acción. ¿Deseas continuar? [s/n]",
        )
        print(texto)
        valor = input("> ")

        if es_afirmacion(valor):
            return continuar_solicitud(solicitud, True, config)

        if es_negacion(valor):
            return continuar_solicitud(solicitud, False, config)

        print("No entendí. Responde sí, no, confirmar, cancelar o detener.")


def _atender_solicitud_legacy(
    solicitud: str | dict[str, Any],
    memoria: dict[str, Any],
    config: dict[str, Any],
) -> Any:
    if isinstance(solicitud, dict):
        print(solicitud.get("texto_confirmacion", "Confirma la accion:"))
    valor = input("> ")
    return completar_solicitud(solicitud, valor, memoria, config)


def ejecutar() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if any(arg in ("-h", "--help") for arg in sys.argv[1:]):
        print(_USO, end="")
        return

    print("Iniciando ORION v2.0...")
    estado = inicializar_orion()
    memoria = estado["memoria"]
    repositorio_notas = estado["repositorio_notas"]
    notas = estado["notas"]
    recordatorios = estado["recordatorios"]
    alias = estado["alias"]
    config = estado["config"]

    def guardar_notas() -> None:
        repositorio_notas.guardar()

    def guardar_alias() -> None:
        guardar_json(ruta_alias(), alias)

    def guardar_config() -> None:
        guardar_json(ruta_configuracion(), config)

    while True:
        try:
            comando = normalizar_comando(input("\nORION> "))
            resultado = procesar(
                comando,
                memoria,
                config,
                notas=notas,
                alias=alias,
                recordatorios=recordatorios,
                guardar_notas=guardar_notas,
                guardar_alias=guardar_alias,
                guardar_config=guardar_config,
                archivo_notas=ruta_notas(),
            )

            mostrar_debug_ia(resultado.debug)

            if not _atender_solicitudes(resultado, memoria, config):
                if resultado.respuesta:
                    print(resultado.respuesta)

            if resultado.salir:
                break
        except (EOFError, KeyboardInterrupt):
            print("\nApagando ORION 👋")
            break


if __name__ == "__main__":
    ejecutar()
