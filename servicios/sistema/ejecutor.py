from __future__ import annotations

import platform
from typing import Any

from servicios.sistema import acciones_pc
from servicios.sistema.capacidades import RegistroCapacidades
from servicios.sistema.contratos import AccionPC, ResultadoAccion
from servicios.sistema.permisos import accion_permitida, requiere_confirmacion


class EjecutorAccionesPC:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.registro = RegistroCapacidades()
        self._registrar_capacidades_base()

    def preparar(self, nombre: str, parametros: dict[str, Any]) -> tuple[ResultadoAccion | None, dict[str, Any] | None]:
        accion = self.registro.obtener(nombre)

        if not accion:
            return ResultadoAccion(False, "Accion no registrada.", nombre, tipo_error="accion_no_registrada"), None

        permitido, motivo = accion_permitida(accion, self.config)
        if not permitido:
            return ResultadoAccion(False, motivo, nombre, tipo_error="accion_no_permitida"), None

        if platform.system() not in accion.sistemas_compatibles:
            return ResultadoAccion(False, "Sistema no compatible.", nombre, tipo_error="sistema_no_compatible"), None

        if requiere_confirmacion(accion, self.config):
            return None, {
                "tipo": "confirmar_accion_pc",
                "identificador": str(
                    parametros.get("aplicacion", nombre)
                ),
                "accion": nombre,
                "datos": {
                    clave: parametros[clave]
                    for clave in accion.parametros_permitidos
                    if clave in parametros
                },
                "parametros": {
                    clave: parametros[clave]
                    for clave in accion.parametros_permitidos
                    if clave in parametros
                },
                "nivel_riesgo": accion.nivel_riesgo,
                "texto_confirmacion": f"Quieres ejecutar {accion.descripcion}?",
            }

        return self.ejecutar(nombre, parametros), None

    def ejecutar(self, nombre: str, parametros: dict[str, Any]) -> ResultadoAccion:
        accion = self.registro.obtener(nombre)

        if not accion:
            return ResultadoAccion(False, "Accion no registrada.", nombre, tipo_error="accion_no_registrada")

        permitidos = {
            clave: parametros[clave]
            for clave in accion.parametros_permitidos
            if clave in parametros
        }
        return accion.ejecutor(**permitidos)

    def _registrar_capacidades_base(self) -> None:
        self.registro.registrar(
            AccionPC(
                nombre="abrir_aplicacion",
                descripcion="abrir una aplicacion registrada",
                parametros_permitidos=["aplicacion"],
                nivel_riesgo="bajo",
                requiere_confirmacion=False,
                sistemas_compatibles=["Windows"],
                ejecutor=acciones_pc.abrir_aplicacion,
            )
        )
        self.registro.registrar(
            AccionPC(
                nombre="cerrar_aplicacion",
                descripcion="cerrar una aplicacion registrada",
                parametros_permitidos=["aplicacion"],
                nivel_riesgo="medio",
                requiere_confirmacion=True,
                sistemas_compatibles=["Windows"],
                ejecutor=acciones_pc.cerrar_aplicacion,
            )
        )
