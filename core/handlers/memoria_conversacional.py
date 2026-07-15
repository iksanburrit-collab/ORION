from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from core.conocimiento import normalizar_para_busqueda
from core.memoria import guardar_memoria, registrar_episodio


CONFIANZA_ALTA = 0.82
CONFIANZA_MEDIA = 0.58


@dataclass
class MemoriaConversacionalDetectada:
    tipo: str
    contenido: str
    categoria: str
    confianza: float


def procesar_memoria_conversacional(
    texto: str,
    memoria: dict[str, Any],
    config: dict[str, Any],
) -> tuple[bool, str, str, dict[str, Any] | None]:
    if not _activada(config):
        return False, "", "", None

    detectada = detectar_memoria_importante(texto)
    if not detectada:
        return False, "", "", None

    minimo = float(
        config.get("memoria_conversacional", {}).get(
            "confianza_minima",
            CONFIANZA_MEDIA,
        )
    )

    if detectada.confianza < minimo:
        return False, "", "", None

    if detectada.confianza >= CONFIANZA_ALTA:
        guardada = guardar_memoria_conversacional(memoria, detectada)
        if guardada:
            guardar_memoria(memoria)
            return (
                True,
                "guardar_memoria_conversacional",
                f"Recordare esto: {detectada.contenido}",
                None,
            )

        return True, "memoria_conversacional_duplicada", "Eso ya estaba guardado.", None

    solicitud = {
        "tipo": "confirmar_memoria",
        "identificador": detectada.contenido,
        "accion": "guardar_memoria_conversacional",
        "datos": {
            "tipo": detectada.tipo,
            "contenido": detectada.contenido,
            "categoria": detectada.categoria,
            "confianza": detectada.confianza,
        },
        "parametros": {
            "tipo": detectada.tipo,
            "contenido": detectada.contenido,
            "categoria": detectada.categoria,
            "confianza": detectada.confianza,
        },
        "nivel_riesgo": "bajo",
        "texto_confirmacion": f"Quieres que recuerde esto? {detectada.contenido}",
    }
    return True, "solicitar_confirmacion_memoria", solicitud["texto_confirmacion"], solicitud


def detectar_memoria_importante(texto: str) -> MemoriaConversacionalDetectada | None:
    limpio = re.sub(r"\s+", " ", texto.strip())
    normalizado = normalizar_para_busqueda(limpio)

    if not _candidato_basico(limpio, normalizado):
        return None

    reglas = [
        (r"\bestoy trabajando en\s+(.+)", "proyecto", "proyectos", 0.88),
        (r"\btrabajo en\s+(.+)", "proyecto", "proyectos", 0.82),
        (r"\bdecidi usar\s+(.+)", "herramienta", "decisiones", 0.9),
        (r"\bdecidí usar\s+(.+)", "herramienta", "decisiones", 0.9),
        (r"\bquiero terminar\s+(.+)", "objetivo", "objetivos", 0.86),
        (r"\bantes de integrar\s+(.+)", "objetivo", "objetivos", 0.62),
        (r"\bcomenzare a estudiar\s+(.+)", "aprendizaje", "estudios", 0.78),
        (r"\bcomenzaré a estudiar\s+(.+)", "aprendizaje", "estudios", 0.78),
        (r"\bestudiare\s+(.+)", "aprendizaje", "estudios", 0.68),
        (r"\bestudiaré\s+(.+)", "aprendizaje", "estudios", 0.68),
        (r"\btuve un problema con\s+(.+)", "correccion", "problemas", 0.72),
        (r"\btuve problemas con\s+(.+)", "correccion", "problemas", 0.72),
        (r"\bmi prioridad es\s+(.+)", "objetivo", "objetivos", 0.86),
    ]

    for patron, tipo, categoria, confianza in reglas:
        coincidencia = re.search(patron, normalizado)
        if not coincidencia:
            continue

        contenido = _extraer_contenido(limpio, coincidencia.group(1))
        if contenido:
            return MemoriaConversacionalDetectada(
                tipo=tipo,
                contenido=contenido,
                categoria=categoria,
                confianza=confianza,
            )

    return None


def guardar_memoria_conversacional(
    memoria: dict[str, Any],
    detectada: MemoriaConversacionalDetectada,
) -> bool:
    return registrar_episodio(
        memoria,
        detectada.tipo,
        detectada.contenido,
        categoria=detectada.categoria,
        fuente="usuario",
        confianza=detectada.confianza,
    )


def confirmar_memoria(solicitud: dict[str, Any], memoria: dict[str, Any]) -> str:
    parametros = solicitud.get("parametros", {})
    if solicitud.get("accion") != "guardar_memoria_conversacional":
        return "No pude completar esa solicitud."
    if str(solicitud.get("identificador", "")) != str(
        parametros.get("contenido", "")
    ):
        return "No pude completar esa solicitud."

    detectada = MemoriaConversacionalDetectada(
        tipo=str(parametros.get("tipo", "")),
        contenido=str(parametros.get("contenido", "")),
        categoria=str(parametros.get("categoria", "otros")),
        confianza=float(parametros.get("confianza", CONFIANZA_MEDIA)),
    )

    if guardar_memoria_conversacional(memoria, detectada):
        guardar_memoria(memoria)
        return f"Listo, lo recordare: {detectada.contenido}"

    return "Eso ya estaba guardado."


def es_confirmacion_afirmativa(texto: str) -> bool:
    return normalizar_para_busqueda(texto) in {"si", "confirmar", "adelante"}


def es_confirmacion_negativa(texto: str) -> bool:
    return normalizar_para_busqueda(texto) in {"no", "cancelar"}


def _activada(config: dict[str, Any]) -> bool:
    datos = config.get("memoria_conversacional", {}) if isinstance(config, dict) else {}
    return datos.get("activada", True)


def _candidato_basico(texto: str, normalizado: str) -> bool:
    if len(normalizado) < 18:
        return False

    if normalizado in {"hola", "hey", "buenas", "gracias"}:
        return False

    if normalizado.endswith("?") or normalizado.startswith(("que ", "como ", "cual ", "cuando ", "donde ")):
        return False

    if normalizado.startswith(("abre ", "cierra ", "agrega tarea", "nueva tarea", "mis tareas", "recuerdame ")):
        return False

    temporales = {"tengo sueno", "tengo sueño", "tengo hambre", "estoy cansado"}
    if any(frase in normalizado for frase in temporales):
        return False

    return bool(texto)


def _extraer_contenido(texto_original: str, fragmento_normalizado: str) -> str:
    palabras = fragmento_normalizado.split()
    if not palabras:
        return ""

    normal_original = normalizar_para_busqueda(texto_original)
    inicio = normal_original.find(fragmento_normalizado)
    if inicio < 0:
        contenido = " ".join(palabras)
    else:
        contenido = texto_original[-len(fragmento_normalizado):]

    contenido = contenido.strip(" .,:;")
    return contenido[:80]
