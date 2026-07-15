from __future__ import annotations

import platform
import re
from typing import Any

from servicios.sistema.aplicaciones import CatalogoAplicaciones
from servicios.sistema.descubrimiento_windows import descubrir_aplicaciones_windows
from servicios.sistema.ejecutor import EjecutorAccionesPC


def puede_manejar_aplicaciones(texto: str) -> bool:
    return bool(
        texto in {
            "escanea aplicaciones",
            "actualiza aplicaciones",
            "lista aplicaciones",
        }
        or re.match(r"^busca aplicacion\s+.+$", texto)
        or re.match(r"^(?:abre|inicia|cierra|termina)\s+.+$", texto)
    )


def procesar_aplicaciones(
    texto: str,
    config: dict[str, Any],
    catalogo: CatalogoAplicaciones | None = None,
) -> tuple[bool, str, str, dict[str, Any] | None]:
    catalogo = catalogo or CatalogoAplicaciones()

    if texto in {"escanea aplicaciones", "actualiza aplicaciones"}:
        if platform.system() != "Windows":
            return True, "escanear_aplicaciones", "El descubrimiento automatico solo esta implementado en Windows.", None

        resumen = catalogo.actualizar_desde_descubrimiento(
            descubrir_aplicaciones_windows()
        )
        respuesta = (
            "Catalogo actualizado. "
            f"Detectadas: {resumen['detectadas']}. "
            f"Nuevas: {resumen['nuevas']}. "
            f"Actualizadas: {resumen['actualizadas']}. "
            f"Sin cambios: {resumen['sin_cambios']}."
        )
        return True, "escanear_aplicaciones", respuesta, None

    if texto == "lista aplicaciones":
        apps = catalogo.listar()
        if not apps:
            return True, "listar_aplicaciones", "No hay aplicaciones registradas.", None

        limite = 20
        visibles = apps[:limite]
        lineas = [f"Aplicaciones registradas: {len(apps)}"]
        lineas.extend(f"- {app.nombre} ({app.origen})" for app in visibles)

        restantes = len(apps) - len(visibles)
        if restantes > 0:
            lineas.append(f"... y {restantes} mas.")

        return True, "listar_aplicaciones", "\n".join(lineas), None

    coincidencia = re.match(r"^busca aplicacion\s+(.+)$", texto)
    if coincidencia:
        app = catalogo.buscar_para_usuario(coincidencia.group(1))
        if not app:
            return True, "buscar_aplicacion", "No encontre esa aplicacion. Quieres agregarla manualmente?", None
        return True, "buscar_aplicacion", f"{app.nombre}: registrada desde {app.origen}", None

    coincidencia = re.match(r"^(?:abre|inicia)\s+(.+)$", texto)
    if coincidencia:
        ejecutor = EjecutorAccionesPC(config)
        resultado, solicitud = ejecutor.preparar(
            "abrir_aplicacion",
            {"aplicacion": coincidencia.group(1).strip()},
        )
        if solicitud:
            return True, "solicitar_abrir_aplicacion", solicitud["texto_confirmacion"], solicitud
        return True, "abrir_aplicacion", resultado.mensaje if resultado else "No pude abrir la aplicacion.", None

    coincidencia = re.match(r"^(?:cierra|termina)\s+(.+)$", texto)
    if coincidencia:
        ejecutor = EjecutorAccionesPC(config)
        resultado, solicitud = ejecutor.preparar(
            "cerrar_aplicacion",
            {"aplicacion": coincidencia.group(1).strip()},
        )
        if solicitud:
            return True, "solicitar_cierre_aplicacion", solicitud["texto_confirmacion"], solicitud
        return True, "cerrar_aplicacion", resultado.mensaje if resultado else "No pude cerrar la aplicacion.", None

    return False, "", "", None


def confirmar_accion_pc(solicitud: dict[str, Any], config: dict[str, Any]) -> str:
    parametros = solicitud.get("parametros", {})
    identificador = str(solicitud.get("identificador", ""))
    if identificador != str(parametros.get("aplicacion", "")):
        return "No pude completar esa solicitud."

    ejecutor = EjecutorAccionesPC(config)
    resultado = ejecutor.ejecutar(
        str(solicitud.get("accion", "")),
        parametros,
    )
    return resultado.mensaje
