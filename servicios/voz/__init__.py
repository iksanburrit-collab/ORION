"""Capa de voz de ORION (STT + TTS), desacoplada del core.

Servicios externos de entrada (microfono -> texto) y salida (texto ->
voz). No importa dependencias externas a nivel de modulo: se resuelven
de forma diferida para que ORION siga funcionando sin la extra de voz.
"""

from __future__ import annotations

from servicios.voz.stt import (
    es_transcripcion_inutil,
    precargar_motor,
    transcribir_audio,
)
from servicios.voz.tts import hablar

__all__ = [
    "es_transcripcion_inutil",
    "hablar",
    "precargar_motor",
    "transcribir_audio",
    "voz_activada",
]


def voz_activada(config: dict | None = None) -> bool:
    """True si la voz (STT o TTS) esta activada en la configuracion."""
    from servicios.voz.stt import stt_activada
    from servicios.voz.tts import tts_activada

    return stt_activada(config) or tts_activada(config)