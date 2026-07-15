from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from utilidades.archivos import cargar_json, guardar_json
from utilidades.rutas import ruta_notas


GuardarFunc = Callable[[], None]
ESTADOS_NOTA = {"activa", "eliminada"}


def fecha_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Nota:
    id: str
    contenido: str
    creada_en: str = field(default_factory=fecha_iso)
    estado: str = "activa"
    actualizada_en: str = field(default_factory=fecha_iso)

    def como_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "contenido": self.contenido,
            "creada_en": self.creada_en,
            "estado": self.estado,
            "actualizada_en": self.actualizada_en,
        }


class RepositorioNotas:
    def __init__(
        self,
        archivo: str | None = None,
        datos: list[Any] | None = None,
        guardar_externo: GuardarFunc | None = None,
    ) -> None:
        self.archivo = archivo or ruta_notas()
        self._guardar_externo = guardar_externo
        self._persistir_archivo = datos is None
        self.error_carga: str | None = None

        if datos is None:
            resultado = cargar_json(self.archivo, [])
            self.error_carga = resultado.error
            self.datos = resultado.datos if isinstance(resultado.datos, list) else []
            persistir_migracion = resultado.error is None
        else:
            self.datos = datos
            persistir_migracion = guardar_externo is not None

        cambio = self._normalizar()
        if cambio and persistir_migracion:
            self.guardar()

    def crear(self, contenido: str) -> Nota:
        nota = Nota(id=self._siguiente_id(), contenido=contenido.strip())
        self.datos.append(nota.como_dict())
        self.guardar()
        return nota

    def listar_activas(self) -> list[Nota]:
        return [
            _nota_desde_dict(item)
            for item in self.datos
            if isinstance(item, dict) and item.get("estado") == "activa"
        ]

    def buscar(self, nota_id: str, estado: str | None = None) -> Nota | None:
        for item in self.datos:
            if not isinstance(item, dict) or str(item.get("id")) != nota_id:
                continue
            if estado and item.get("estado") != estado:
                return None
            return _nota_desde_dict(item)
        return None

    def eliminar(self, nota_id: str) -> bool:
        for item in self.datos:
            if (
                isinstance(item, dict)
                and str(item.get("id")) == nota_id
                and item.get("estado") == "activa"
            ):
                item["estado"] = "eliminada"
                item["actualizada_en"] = fecha_iso()
                self.guardar()
                return True
        return False

    def eliminar_todas(self) -> int:
        cantidad = 0
        ahora = fecha_iso()
        for item in self.datos:
            if isinstance(item, dict) and item.get("estado") == "activa":
                item["estado"] = "eliminada"
                item["actualizada_en"] = ahora
                cantidad += 1

        if cantidad:
            self.guardar()
        return cantidad

    def guardar(self) -> None:
        if self._guardar_externo:
            self._guardar_externo()
        elif self._persistir_archivo:
            guardar_json(self.archivo, self.datos)

    def _normalizar(self) -> bool:
        ahora = fecha_iso()
        usados: set[str] = set()
        normalizados: list[dict[str, str]] = []
        cambio = False

        for indice, item in enumerate(self.datos, start=1):
            if isinstance(item, str):
                contenido = item.strip()
                if not contenido:
                    cambio = True
                    continue
                nota = Nota(
                    id=_id_disponible(indice, usados),
                    contenido=contenido,
                    creada_en=ahora,
                    actualizada_en=ahora,
                )
                cambio = True
            elif isinstance(item, dict):
                contenido = str(item.get("contenido", item.get("nota", ""))).strip()
                if not contenido:
                    cambio = True
                    continue
                nota_id = str(item.get("id", "")).strip()
                if not nota_id or nota_id in usados:
                    nota_id = _id_disponible(indice, usados)
                    cambio = True
                estado = str(item.get("estado", "activa"))
                if estado not in ESTADOS_NOTA:
                    estado = "activa"
                    cambio = True
                creada = str(item.get("creada_en") or ahora)
                actualizada = str(item.get("actualizada_en") or creada)
                nota = Nota(nota_id, contenido, creada, estado, actualizada)
                cambio = cambio or item != nota.como_dict()
            else:
                cambio = True
                continue

            usados.add(nota.id)
            normalizados.append(nota.como_dict())

        if normalizados != self.datos:
            self.datos[:] = normalizados
            cambio = True
        return cambio

    def _siguiente_id(self) -> str:
        usados = {
            str(item.get("id"))
            for item in self.datos
            if isinstance(item, dict)
        }
        return _id_disponible(1, usados)


def _id_disponible(inicio: int, usados: set[str]) -> str:
    indice = max(1, inicio)
    while f"nota-{indice}" in usados:
        indice += 1
    return f"nota-{indice}"


def _nota_desde_dict(datos: dict[str, Any]) -> Nota:
    return Nota(
        id=str(datos.get("id", "")),
        contenido=str(datos.get("contenido", "")),
        creada_en=str(datos.get("creada_en", "")),
        estado=str(datos.get("estado", "activa")),
        actualizada_en=str(datos.get("actualizada_en", "")),
    )
