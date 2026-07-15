import sys

from core.cerebro import completar_solicitud, procesar
from core.memoria import guardar_memoria, inicializar_memoria
from servicios.calendario.legacy import migrar_recordatorios_legacy
from servicios.notas import RepositorioNotas
from utilidades.archivos import asegurar_json, cargar_json, guardar_json
from utilidades.rutas import (
    ruta_alias,
    ruta_configuracion,
    ruta_memoria,
    ruta_notas,
    ruta_recordatorios,
)
from utilidades.texto import normalizar_comando
from utilidades.configuracion import cargar_configuracion

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("Iniciando ORION v2.0...")


resultado_memoria = cargar_json(ruta_memoria(), {})
memoria = inicializar_memoria(resultado_memoria.datos)
repositorio_notas = RepositorioNotas(ruta_notas())
notas = repositorio_notas.datos
resultado_recordatorios = cargar_json(ruta_recordatorios(), [])
recordatorios = (
    resultado_recordatorios.datos
    if isinstance(resultado_recordatorios.datos, list)
    else []
)
alias = asegurar_json(ruta_alias(), {})
config = cargar_configuracion(ruta_configuracion())

if resultado_memoria.error is None:
    guardar_memoria(memoria, ruta_memoria())


def guardar_notas():
    repositorio_notas.guardar()


def guardar_recordatorios():
    guardar_json(ruta_recordatorios(), recordatorios)


def guardar_alias():
    guardar_json(ruta_alias(), alias)


def guardar_config():
    guardar_json(ruta_configuracion(), config)


if resultado_recordatorios.error is None:
    migrar_recordatorios_legacy(
        recordatorios,
        guardar_recordatorios=guardar_recordatorios,
    )


def mostrar_debug_ia(debug):
    if not debug:
        return

    proveedor = str(debug.get("proveedor", "")).upper()
    tiempo = debug.get("tiempo_respuesta")

    if tiempo is not None:
        print("Tiempo:")
        print(f"{tiempo:.2f} s")
        
while True:
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

    if resultado.respuesta:
        print(resultado.respuesta)

    mostrar_debug_ia(resultado.debug)

    solicitud = resultado.solicitud_pendiente or resultado.solicitud
    if solicitud:
        if isinstance(solicitud, dict):
            print(solicitud.get("texto_confirmacion", "Confirma la accion:"))
        valor = input("> ")
        resultado_solicitud = completar_solicitud(
            solicitud,
            valor,
            memoria,
            config,
        )
        if resultado_solicitud.respuesta:
            print(resultado_solicitud.respuesta)

    if resultado.salir:
        break
