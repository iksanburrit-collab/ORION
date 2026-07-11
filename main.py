import sys

from core.cerebro import completar_solicitud, procesar
from core.memoria import guardar_memoria, inicializar_memoria
from utilidades.archivos import asegurar_json, cargar, guardar_json
from utilidades.texto import normalizar_comando


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("Iniciando ORION v1.8...")


memoria = inicializar_memoria(cargar("memoria.json", {}))
notas = asegurar_json("notas.json", [])
recordatorios = asegurar_json("recordatorios.json", [])
alias = asegurar_json("alias.json", {})
config = asegurar_json("config.json", {"modo": "normal"})
guardar_memoria(memoria)


def guardar_notas():
    guardar_json("notas.json", notas)


def guardar_recordatorios():
    guardar_json("recordatorios.json", recordatorios)


def guardar_alias():
    guardar_json("alias.json", alias)


def guardar_config():
    guardar_json("config.json", config)


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
    )

    if resultado.get("respuesta"):
        print(resultado["respuesta"])

    solicitud = resultado.get("solicitud")
    if solicitud:
        valor = input("> ")
        resultado_solicitud = completar_solicitud(
            solicitud,
            valor,
            memoria,
            config,
        )
        if resultado_solicitud.get("respuesta"):
            print(resultado_solicitud["respuesta"])

    if resultado.get("salir"):
        break