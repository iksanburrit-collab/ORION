"""Orquestador de voz de ORION: wake word -> captura -> transcripcion.

Coordina el ciclo de estados de la activacion por voz:

  ESPERA_WAKEWORD -> WAKEWORD_DETECTADO -> CAPTURA_COMANDO
                  -> TRANSCRIPCION -> (callback) -> ESPERA_WAKEWORD

Abre UN solo InputStream de sounddevice y lo comparte entre el detector
de wake word y el VAD de captura (nunca hay dos flujos de microfono
abiertos a la vez). No transcribe por su cuenta la wake word y no llama
al cerebro: entrega el texto del comando al callback y deja que main.py
siga su flujo normal. Todo es local/offline: el audio no sale de la
maquina.

El detector queda en cooldown mientras se atiende el comando y durante
un margen despues, para que el audio del TTS (que se reproduce mientras
el callback atiende la respuesta) no provoque una reactivacion inmediata.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from servicios.voz.stt import (
    RATE_MUESTREO,
    _aceptar_captura,
    _audio_desde_bloques,
    _capturar_voz,
    es_transcripcion_inutil,
    transcribir_audio,
)
from servicios.voz.wakeword import (
    TAMANO_TRAMO,
    _obtener_detector,
    wakeword_activada,
)


def _config_voz(config: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    voz = config.get("voz", {})
    return voz if isinstance(voz, dict) else {}


def _importar_captura() -> tuple[Any, Any]:
    """Importa numpy y sounddevice. Lanza ImportError si faltan."""
    import numpy as np
    import sounddevice as sd

    return np, sd


def _leer_tramo(flujo: Any, np: Any) -> Any:
    """Lee un tramo de 1280 muestras (80 ms) y lo aplana a float32."""
    tramo, _desbordado = flujo.read(TAMANO_TRAMO)
    return np.asarray(tramo, dtype=np.float32).reshape(-1)


def _esperar_wakeword(
    detector: Any,
    flujo: Any,
    np: Any,
    reloj: Any | None = None,
) -> bool:
    """Estado ESPERA_WAKEWORD: alimenta el detector hasta que activa.

    Durante el cooldown solo drena el flujo (sin alimentar el modelo):
    asi se descarta el audio residual del TTS sin gastar CPU y sin
    riesgo de reactivacion. Devuelve True al detectar la frase.
    """
    reloj = reloj or time.monotonic

    while True:
        tramo = _leer_tramo(flujo, np)

        if detector.en_cooldown():
            continue

        if detector.procesar(tramo):
            return True


def _capturar_y_transcribir(
    flujo: Any,
    np: Any,
    config: dict[str, Any] | None,
    reloj: Any | None = None,
) -> str:
    """Estado CAPTURA_COMANDO + TRANSCRIPCION sobre el mismo flujo.

    Reutiliza el VAD adaptativo de stt.py para esperar el inicio del
    habla y recortar por silencio, y la puerta de calidad SNR/duracion
    para no enviar ruido a Whisper. Devuelve el texto del comando ("" si
    no se entendio nada).
    """
    voz = _config_voz(config)
    stt = voz.get("stt", {})
    max_duracion = float(stt.get("max_duracion_segundos", 6) or 6)
    silencio = float(stt.get("silencio_segundos", 0.6) or 0.6)

    bloques, suelo_ruido, bloques_habla = _capturar_voz(
        flujo,
        np,
        max_duracion=max_duracion,
        silencio=silencio,
        reloj=reloj,
    )

    if not _aceptar_captura(bloques, suelo_ruido, bloques_habla, np):
        return ""

    audio = _audio_desde_bloques(bloques, np)
    if audio is None:
        return ""

    return transcribir_audio(audio=audio, config=config)


def bucle_escucha(
    config: dict[str, Any] | None,
    al_recibir_texto: Callable[[str], bool] | None = None,
) -> None:
    """Ejecuta el ciclo de voz con wake word hasta salir o fallar.

    `al_recibir_texto(texto)` recibe cada comando transcrito y devuelve
    True para seguir escuchando o False para terminar el bucle (por
    ejemplo, cuando el comando fue "salir"). Si no se entrega callback,
    el bucle transcribe y no hace nada con el texto (modo vigilancia).

    No-op si la wake word no esta activa, si falta openwakeword, si el
    modelo no cargo o si falta el microfono: ORION nunca se rompe y cae
    en el flujo por teclado/transcripcion normal.
    """
    if config is None:
        return

    if not wakeword_activada(config):
        return

    detector = _obtener_detector()
    detector._cargar(config)

    if not detector.cargado():
        return

    try:
        np, sd = _importar_captura()
    except Exception:
        return

    try:
        with sd.InputStream(
            samplerate=RATE_MUESTREO,
            channels=1,
            dtype="float32",
        ) as flujo:
            while True:
                if not _esperar_wakeword(detector, flujo, np):
                    return

                # WAKEWORD_DETECTADO: entra en cooldown para que el propio
                # audio de la frase o la respuesta del TTS no reactiven.
                detector.iniciar_cooldown()

                texto = _capturar_y_transcribir(flujo, np, config)

                if texto and not es_transcripcion_inutil(texto):
                    if al_recibir_texto is not None:
                        seguir = al_recibir_texto(texto)
                        if not seguir:
                            return
                else:
                    # Se activo pero no se entendio una orden: vuelve a
                    # ESPERA_WAKEWORD sin molestar al proveedor de IA.
                    pass

                # Refresca el cooldown antes de volver a ESPERA: el TTS
                # ya termino (hablar es bloqueante) y el margen extra
                # absorbe el eco residual de los altavoces en el micro.
                detector.iniciar_cooldown()
    except Exception:
        return