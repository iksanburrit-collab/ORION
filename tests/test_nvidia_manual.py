from __future__ import annotations

import os
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from ia.nvidia import generar_respuesta_nvidia_diagnostico


def main() -> None:
    diagnostico = generar_respuesta_nvidia_diagnostico(
        "Responde con una frase corta para diagnosticar la conexion.",
        contexto="Diagnostico manual de ORION.",
    )

    print(f"API detectada: {'si' if diagnostico.api_detectada else 'no'}")
    print(f"Endpoint: {diagnostico.endpoint}")
    print(f"Modelo: {diagnostico.modelo}")
    print(f"HTTP: {diagnostico.http}")
    print(f"Tiempo: {diagnostico.tiempo:.2f} s")
    print(f"Respuesta: {diagnostico.texto[:100]}")


if __name__ == "__main__":
    main()
