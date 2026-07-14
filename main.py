import sys

from core.cerebro import completar_solicitud, procesar
from core.memoria import guardar_memoria, inicializar_memoria
from utilidades.archivos import asegurar_json, cargar, guardar_json
from utilidades.texto import normalizar_comando


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("Iniciando ORION v2.0...")


memoria = inicializar_memoria(cargar("memoria.json", {}))
notas = asegurar_json("notas.json", [])
recordatorios = asegurar_json("recordatorios.json", [])
alias = asegurar_json("alias.json", {})
config = asegurar_json(
    "config.json",
    {
        "modo": "normal",
        "ia": {
            "activada": True,
            "proveedor": "nvidia",
            "fallback_local": False,
            "nvidia": {
                "modelo": "meta/llama-4-maverick-17b-128e-instruct",
                "timeout": 10,
                "max_tokens": 180,
            },
            "ollama": {
                "modelo": "qwen3:1.7b",
                "timeout": 60,
                "keep_alive": "10m",
                "num_predict": 100,
                "num_ctx": 2048,
            },
            "limite_contexto": 900,
            "max_turnos": 4,
            "debug_rendimiento": True,
        },
    },
)
guardar_memoria(memoria)


def guardar_notas():
    guardar_json("notas.json", notas)


def guardar_recordatorios():
    guardar_json("recordatorios.json", recordatorios)


def guardar_alias():
    guardar_json("alias.json", alias)


def guardar_config():
    guardar_json("config.json", config)


def mostrar_debug_ia(debug):
    if not debug:
        return

    if debug.get("lineas_debug") or debug.get("nvidia", {}).get("lineas_debug"):
        return

    proveedor = str(debug.get("proveedor", "")).upper()
    tiempo = debug.get("tiempo_respuesta")

    print("[IA DEBUG]")
    print("Proveedor:")
    print(proveedor or "Desconocido")

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
    )

    if resultado.respuesta:
        print(resultado.respuesta)

    mostrar_debug_ia(resultado.debug)

    solicitud = resultado.solicitud
    if solicitud:
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
