"""Deteccion de wake word de ORION, desacoplada del STT y del TTS.

El detector recibe tramos de audio de 1280 muestras (80 ms a 16 kHz),
los pasa al modelo openwakeword (backend ONNX, 100 % local/offline) y
devuelve True cuando la frase de activacion supera el umbral configurado
fuera del periodo de cooldown. No transcribe, no habla y no llama al
cerebro: solo decide si el estado debe pasar de ESPERA a ACTIVO.

Los imports de dependencias externas son diferidos: un ORION sin la
extra de voz o sin openwakeword nunca debe romper el flujo.
"""

from __future__ import annotations

import threading
import time
from typing import Any

RATE_MUESTREO = 16000
TAMANO_TRAMO = 1280          # 80 ms a 16 kHz (marco de openwakeword)
UMBRAL_DEFECTO = 0.5         # puntuacion del modelo a partir de la cual se activa
COOLDOWN_DEFECTO_SEGUNDOS = 2.0

# Modelos de voz embebidos en el wheel de openwakeword 0.4.0. "orion" no
# existe como modelo preentrenado: se puede usar una ruta a un .onnx
# propio en voz.wakeword.modelo (queda reservado para una fase futura).
MODELOS_EMBEBIDOS = ("hey_jarvis")


def _config_voz(config: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    voz = config.get("voz", {})
    return voz if isinstance(voz, dict) else {}


def _config_wakeword(config: dict[str, Any] | None) -> dict[str, Any]:
    voz = _config_voz(config)
    wakeword = voz.get("wakeword", {})
    return wakeword if isinstance(wakeword, dict) else {}


def wakeword_activada(config: dict[str, Any] | None) -> bool:
    voz = _config_voz(config)
    if not voz.get("activada", False):
        return False
    return bool(_config_wakeword(config).get("activada", False))


def _config_por_defecto() -> dict[str, Any] | None:
    """Carga la configuracion real de ORION. None si falla cualquier cosa."""
    try:
        from utilidades.configuracion import cargar_configuracion
        from utilidades.rutas import ruta_configuracion

        return cargar_configuracion(ruta_configuracion())
    except Exception:
        return None


def _importar_openwakeword() -> Any:
    """Importa openwakeword. Lanza ImportError si no esta disponible."""
    import openwakeword

    return openwakeword


def _resolver_modelo(modelo: str, openwakeword: Any) -> str | None:
    """Devuelve la ruta del modelo .onnx a cargar.

    Acepta un nombre embebido ("hey_jarvis", "alexa", ...) o una ruta
    directa a un archivo .onnx (modelo custom, p. ej. un futuro "orion").
    None si no se puede resolver.
    """
    if not modelo:
        return None

    if modelo.endswith(".onnx"):
        try:
            from pathlib import Path

            if Path(modelo).is_file():
                return modelo
        except Exception:
            return None
        return None

    try:
        embebidos = openwakeword.models
        if modelo in embebidos:
            return embebidos[modelo]["model_path"]
    except Exception:
        return None

    return None


class WakeWordDetector:
    """Detector openwakeword cargado una sola vez (singleton).

    `procesar` recibe un tramo de 1280 muestras float32 a 16 kHz y
    devuelve True si la frase de activacion se detecta fuera del
    cooldown. Durante el cooldown ignora el audio (no provoca una
    reactivacion inmediata tras la respuesta del TTS).
    """

    def __init__(self) -> None:
        self._modelo: Any | None = None
        self._error: Exception | None = None
        self._umbral = UMBRAL_DEFECTO
        self._cooldown_segundos = COOLDOWN_DEFECTO_SEGUNDOS
        self._cooldown_hasta = 0.0

    def _cargar(self, config: dict[str, Any] | None) -> None:
        if self._modelo is not None or self._error is not None:
            return

        try:
            openwakeword = _importar_openwakeword()
        except Exception as exc:
            self._error = exc
            return

        wakeword = _config_wakeword(config)
        modelo = str(wakeword.get("modelo", "hey_jarvis") or "hey_jarvis")
        self._umbral = float(wakeword.get("umbral", UMBRAL_DEFECTO) or UMBRAL_DEFECTO)
        self._cooldown_segundos = float(
            wakeword.get("cooldown_segundos", COOLDOWN_DEFECTO_SEGUNDOS)
            or COOLDOWN_DEFECTO_SEGUNDOS
        )

        ruta = _resolver_modelo(modelo, openwakeword)
        if ruta is None:
            self._error = ValueError(f"modelo de wake word no encontrado: {modelo!r}")
            return

        try:
            self._modelo = openwakeword.Model(wakeword_model_paths=[ruta])
        except Exception as exc:
            self._error = exc

    def cargado(self) -> bool:
        """True si el modelo quedo disponible para detectar."""
        return self._modelo is not None

    def en_cooldown(self) -> bool:
        """True si el detector debe ignorar audio (tras una respuesta TTS)."""
        return time.monotonic() < self._cooldown_hasta

    def iniciar_cooldown(self) -> None:
        self._cooldown_hasta = time.monotonic() + self._cooldown_segundos

    def reiniciar(self) -> None:
        """Limpia el estado tras una activacion (fuera del cooldown)."""
        self._cooldown_hasta = 0.0

    def procesar(self, tramo: Any) -> bool:
        """Devuelve True si el tramo activa el wake word fuera del cooldown."""
        if self._modelo is None or self.en_cooldown():
            return False

        try:
            prediccion = self._modelo.predict(tramo)
        except Exception:
            return False

        return any(float(puntuacion) >= self._umbral for puntuacion in prediccion.values())


_detector_lock = threading.Lock()
_detector: WakeWordDetector | None = None


def _obtener_detector() -> WakeWordDetector:
    """Devuelve el detector compartido (una sola instancia por proceso)."""
    global _detector

    if _detector is None:
        with _detector_lock:
            if _detector is None:
                _detector = WakeWordDetector()

    return _detector


def precargar_wakeword(config: dict[str, Any] | None = None) -> bool:
    """Precarga el detector de wake word reutilizando el singleton.

    Solo actua si voz.activada y voz.wakeword.activada son true.
    Devuelve True si el detector quedo disponible, y False si la wake
    word esta desactivada, si falta openwakeword o si el modelo no
    cargo: ORION debe continuar por teclado/transcripcion normal.
    """
    if config is None:
        config = _config_por_defecto()

    if not wakeword_activada(config):
        return False

    try:
        detector = _obtener_detector()
        detector._cargar(config)
        return detector.cargado()
    except Exception:
        return False