from __future__ import annotations

from core.conocimiento.terminos import ALIAS_GUSTOS
from core.conocimiento.terminos import ARTICULOS_INICIALES
from core.conocimiento.terminos import CATEGORIAS_APRENDIZAJE
from core.conocimiento.terminos import CATEGORIAS_APRENDIZAJE_MEMORIA
from core.conocimiento.terminos import CATEGORIAS_GUSTOS
from core.conocimiento.terminos import CATEGORIAS_GUSTOS_MEMORIA
from core.conocimiento.terminos import CATEGORIAS_HERRAMIENTAS
from core.conocimiento.terminos import CATEGORIAS_HERRAMIENTAS_MEMORIA
from core.conocimiento.terminos import CATEGORIA_POR_CONTEXTO
from core.conocimiento.terminos import ClasificacionGusto
from core.conocimiento.terminos import ConocimientoDetectado
from core.conocimiento.terminos import ENTIDADES_CANONICAS
from core.conocimiento.terminos import ENTIDADES_CATEGORIAS_GUSTOS
from core.conocimiento.terminos import PALABRAS_CLAVE_GUSTOS
from core.conocimiento.terminos import PATRONES_GUSTOS
from core.conocimiento.terminos import RELACIONES_SEMANTICAS
from core.conocimiento.normalizacion import canonizar_entidad
from core.conocimiento.normalizacion import inferir_relaciones_semanticas
from core.conocimiento.normalizacion import limpiar_valor
from core.conocimiento.normalizacion import normalizar_para_busqueda
from core.conocimiento.clasificacion import clasificar_aprendizaje
from core.conocimiento.clasificacion import clasificar_gusto
from core.conocimiento.clasificacion import clasificar_herramienta
from core.conocimiento.deteccion import detectar_conocimiento


__all__ = [
    "ALIAS_GUSTOS",
    "ARTICULOS_INICIALES",
    "CATEGORIAS_APRENDIZAJE",
    "CATEGORIAS_APRENDIZAJE_MEMORIA",
    "CATEGORIAS_GUSTOS",
    "CATEGORIAS_GUSTOS_MEMORIA",
    "CATEGORIAS_HERRAMIENTAS",
    "CATEGORIAS_HERRAMIENTAS_MEMORIA",
    "CATEGORIA_POR_CONTEXTO",
    "ClasificacionGusto",
    "ConocimientoDetectado",
    "ENTIDADES_CANONICAS",
    "ENTIDADES_CATEGORIAS_GUSTOS",
    "PALABRAS_CLAVE_GUSTOS",
    "PATRONES_GUSTOS",
    "RELACIONES_SEMANTICAS",
    "canonizar_entidad",
    "clasificar_aprendizaje",
    "clasificar_gusto",
    "clasificar_herramienta",
    "detectar_conocimiento",
    "inferir_relaciones_semanticas",
    "limpiar_valor",
    "normalizar_para_busqueda",
]
