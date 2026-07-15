from __future__ import annotations

import re


_COMANDOS_RESERVADOS = (
    (
        re.compile(r"^(?:nota|notas)\b|^(?:anota|recuerda)(?:\s|$)|^(?:mis|lista|borra|elimina|borrar)\s+notas?\b"),
        "Comandos de notas: \"anota <texto>\", \"mis notas\", \"borra nota <id>\" o \"borrar notas\".",
    ),
    (
        re.compile(r"^(?:memoria|memorias)\b|^(?:mis|lista|olvida|borra|borrar|elimina)\s+memorias?\b"),
        "Comandos de memoria: \"mis memorias\", \"olvida memoria <id>\" o \"borra memoria <id>\".",
    ),
    (
        re.compile(r"^(?:tarea|tareas)\b|^(?:agrega|nueva|mis|lista|completa|borra|elimina)\s+tareas?\b"),
        "Comandos de tareas: \"agrega tarea <texto>\", \"mis tareas\" o \"elimina tarea <id>\".",
    ),
    (
        re.compile(r"^(?:recordatorio|recordatorios)\b|^recuerdame(?:\s|$)|^(?:mis|lista|borra|elimina|crea|agrega)\s+recordatorios?\b"),
        "Usa \"recuerdame <texto>\" para crear un recordatorio.",
    ),
    (
        re.compile(r"^(?:evento|eventos)\b|^(?:crea|mis|lista|borra|elimina)\s+eventos?\b"),
        "Usa \"crea evento <texto> el YYYY-MM-DD a las HH:MM\" o \"mis eventos\".",
    ),
    (
        re.compile(r"^(?:aplicacion|aplicaciones)\b|^(?:busca|mis|lista|escanea|actualiza)\s+aplicaciones?\b"),
        "Comandos de aplicaciones: \"busca aplicacion <nombre>\", \"lista aplicaciones\" o \"escanea aplicaciones\".",
    ),
)


def ayuda_comando_local_invalido(texto: str) -> str | None:
    for patron, ayuda in _COMANDOS_RESERVADOS:
        if patron.search(texto):
            return ayuda
    return None
