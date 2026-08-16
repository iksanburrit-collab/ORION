from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re

from core.conocimiento import normalizar_para_busqueda
from servicios.sistema.contratos import AplicacionRegistrada
from utilidades.archivos import cargar, guardar_json
from utilidades.rutas import ruta_aplicaciones_usuario


# Formatos de lanzamiento habituales en las plataformas compatibles. Se sigue
# rechazando cualquier ruta que pueda convertirse en una cadena de comandos.
EXTENSIONES_PERMITIDAS = {".app", ".desktop", ".exe", ".lnk"}


class CatalogoAplicaciones:
    def __init__(self, archivo: str | None = None) -> None:
        self.archivo = archivo or ruta_aplicaciones_usuario()
        self.aplicaciones = self._cargar()
        self._descubrimiento_hecho = False

    def listar(self) -> list[AplicacionRegistrada]:
        self._descubrir_si_necesario()
        return sorted(self.aplicaciones, key=lambda app: app.nombre.lower())

    def buscar_por_identidad(
        self,
        aplicacion: AplicacionRegistrada,
    ) -> AplicacionRegistrada | None:
        identidad = identidad_aplicacion(aplicacion)
        for existente in self.aplicaciones:
            if identidad_aplicacion(existente) == identidad:
                return existente
        return None

    def buscar_para_usuario(self, nombre: str) -> AplicacionRegistrada | None:
        self._descubrir_si_necesario()
        clave = normalizar_para_busqueda(nombre)

        for app in self.aplicaciones:
            claves = [app.nombre] + app.aliases
            if any(normalizar_para_busqueda(item) == clave for item in claves):
                return app

        for app in self.aplicaciones:
            claves = [app.nombre] + app.aliases
            if any(clave in normalizar_para_busqueda(item) for item in claves):
                return app

        return None

    def buscar(self, nombre: str) -> AplicacionRegistrada | None:
        return self.buscar_para_usuario(nombre)

    def agregar_manual(
        self,
        nombre: str,
        ruta: str,
        aliases: list[str] | None = None,
    ) -> AplicacionRegistrada:
        if not ruta_permitida(ruta):
            raise ValueError("Ruta de aplicacion no permitida")

        app = AplicacionRegistrada(
            nombre=nombre.strip(),
            aliases=aliases or [],
            ruta=ruta,
            origen="manual",
            verificada=os.path.exists(ruta),
            ultima_deteccion=_fecha_iso(),
        )
        existente = self.buscar_por_identidad(app)

        if existente:
            existente.aliases = sorted(set(existente.aliases + app.aliases))
            existente.ruta = app.ruta
            existente.verificada = app.verificada
            existente.ultima_deteccion = app.ultima_deteccion
        else:
            self.aplicaciones.append(app)

        self.guardar()
        return app

    def actualizar_desde_descubrimiento(
        self,
        detectadas: list[AplicacionRegistrada],
    ) -> dict[str, int]:
        resumen = {
            "detectadas": len(detectadas),
            "nuevas": 0,
            "actualizadas": 0,
            "sin_cambios": 0,
            "ignoradas": 0,
        }

        for detectada in detectadas:
            if not detectada.nombre or (
                detectada.ruta and not ruta_permitida(detectada.ruta)
            ):
                resumen["ignoradas"] += 1
                continue

            existente = self.buscar_por_identidad(detectada)
            if existente:
                if _misma_aplicacion(existente, detectada):
                    resumen["sin_cambios"] += 1
                    continue

                existente.nombre = detectada.nombre
                existente.ruta = detectada.ruta
                existente.aliases = sorted(set(existente.aliases + detectada.aliases))
                existente.tipo = detectada.tipo
                existente.origen = detectada.origen
                existente.verificada = detectada.verificada
                existente.ultima_deteccion = detectada.ultima_deteccion
                resumen["actualizadas"] += 1
            else:
                self.aplicaciones.append(detectada)
                resumen["nuevas"] += 1

        if resumen["nuevas"] or resumen["actualizadas"]:
            self.guardar()

        return resumen

    def _descubrir_si_necesario(self) -> None:
        if self._descubrimiento_hecho or self.aplicaciones:
            return

        self._descubrimiento_hecho = True

        for detectada in _descubrir_aplicaciones_por_plataforma():
            if not detectada.nombre or (
                detectada.ruta and not ruta_permitida(detectada.ruta)
            ):
                continue

            if self.buscar_por_identidad(detectada) is None:
                self.aplicaciones.append(detectada)

    def guardar(self) -> None:
        directorio = os.path.dirname(self.archivo)
        if directorio:
            os.makedirs(directorio, exist_ok=True)

        guardar_json(
            self.archivo,
            {
                "version": 1,
                "aplicaciones": [app.como_dict() for app in self.aplicaciones],
            },
        )

    def _cargar(self) -> list[AplicacionRegistrada]:
        datos = cargar(self.archivo, {"aplicaciones": []})

        if not isinstance(datos, dict):
            return []

        apps = []
        for item in datos.get("aplicaciones", []):
            if not isinstance(item, dict):
                continue

            app = AplicacionRegistrada.desde_dict(item)
            if app.nombre and (not app.ruta or ruta_permitida(app.ruta)):
                apps.append(app)

        return apps


def ruta_permitida(ruta: str) -> bool:
    if not isinstance(ruta, str) or not ruta.strip():
        return False

    if re.search(r"\s(?:/|--)|[;&|<>]", ruta):
        return False

    extension = Path(ruta).suffix.lower()
    return extension in EXTENSIONES_PERMITIDAS


def identidad_aplicacion(aplicacion: AplicacionRegistrada) -> str:
    ruta = str(aplicacion.ruta or "").strip()
    if ruta:
        normalizada = os.path.normpath(os.path.expanduser(ruta)).casefold()
        return f"ruta:{normalizada}"

    nombre = normalizar_para_busqueda(aplicacion.nombre)
    origen = normalizar_para_busqueda(aplicacion.origen)
    tipo = normalizar_para_busqueda(aplicacion.tipo)
    return f"datos:{nombre}|{origen}|{tipo}"


def _fecha_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _misma_aplicacion(
    existente: AplicacionRegistrada,
    detectada: AplicacionRegistrada,
) -> bool:
    return (
        existente.nombre == detectada.nombre
        and existente.ruta == detectada.ruta
        and existente.tipo == detectada.tipo
        and set(existente.aliases) == set(existente.aliases + detectada.aliases)
        and existente.origen == detectada.origen
        and existente.verificada == detectada.verificada
    )


def _descubrir_aplicaciones_por_plataforma() -> list[AplicacionRegistrada]:
    sistema = platform.system()
    if sistema == "Linux":
        from servicios.sistema.descubrimiento_linux import descubrir_aplicaciones_linux

        return descubrir_aplicaciones_linux()
    if sistema == "Windows":
        from servicios.sistema.descubrimiento_windows import descubrir_aplicaciones_windows

        return descubrir_aplicaciones_windows()
    return []
