"""STT (Speech-to-Text) de ORION, desacoplado del core.

Motor por defecto: faster-whisper en CPU/int8. Captura con sounddevice.
Los imports de dependencias externas son diferidos: un ORION sin la
extra de voz, sin microfono o sin modelo nunca debe romper el flujo.
"""

from __future__ import annotations

import re
import threading
import time
from statistics import median
from typing import Any, Protocol

RATE_MUESTREO = 16000
TAMANO_BLOQUE = 1600          # 100 ms a 16 kHz
UMBRAL_SILENCIO = 0.01        # RMS bajo el cual se considera silencio absoluto
UMBRAL_INICIO_HABLA = 0.02    # RMS minimo absoluto para iniciar la grabacion
UMBRAL_RECORTE = 0.005        # amplitud minima para recortar bordes de silencio

# VAD adaptativo: el inicio del habla y el mantenimiento de la grabacion se
# calculan a partir del suelo de ruido ambiente (multiplicadores).
FACTOR_INICIO_HABLA = 6.0     # rms > suelo * 6 dispara la grabacion
FACTOR_HABLA = 2.0            # rms >= suelo * 2 se mantiene "habla" (histeresis)
GANANCIA_SNR = 4.0            # ~12 dB: pico de la captura vs suelo de ruido
MIN_BLOQUES_HABLA = 3         # 300 ms minimos de habla para aceptar la captura
VENTANA_RUIDO = 10            # bloques (1 s) usados para estimar el suelo


class STTEngine(Protocol):
    """Contrato de un motor de transcripcion."""

    def transcribir(self, audio: Any, config: dict[str, Any] | None = None) -> str:
        """Transcribe audio (numpy float32 o bytes PCM16 mono) a texto."""
        ...


def _config_voz(config: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    voz = config.get("voz", {})
    return voz if isinstance(voz, dict) else {}


def stt_activada(config: dict[str, Any] | None) -> bool:
    voz = _config_voz(config)
    if not voz.get("activada", False):
        return False
    stt = voz.get("stt", {})
    return bool(stt.get("activada", False))


def _config_por_defecto() -> dict[str, Any] | None:
    """Carga la configuracion real de ORION. None si falla cualquier cosa."""
    try:
        from utilidades.configuracion import cargar_configuracion
        from utilidades.rutas import ruta_configuracion

        return cargar_configuracion(ruta_configuracion())
    except Exception:
        return None


def _importar_motor() -> Any:
    """Importa faster-whisper. Lanza ImportError si no esta disponible."""
    from faster_whisper import WhisperModel

    return WhisperModel


def _importar_captura() -> tuple[Any, Any]:
    """Importa numpy y sounddevice. Lanza ImportError si faltan."""
    import numpy as np
    import sounddevice as sd

    return np, sd


def _precalentar_vad() -> None:
    """Precalienta el VAD de faster-whisper (Silero) reutilizando su caché.

    faster-whisper carga onnxruntime y el modelo Silero de forma perezosa
    en la primera transcripcion real (~0.6 s medidos). Llamarlo durante la
    precarga adelanta ese coste al arranque. No-op si falla cualquier cosa:
    la transcripcion funciona igual, solo tarda un poco mas la primera vez.
    """
    try:
        from faster_whisper.vad import get_vad_model

        get_vad_model()
    except Exception:
        return


class FasterWhisperSTT:
    """Motor faster-whisper en CPU/int8 con modelo cargado una sola vez."""

    def __init__(self) -> None:
        self._modelo: Any | None = None
        self._error: Exception | None = None

    def transcribir(self, audio: Any, config: dict[str, Any] | None = None) -> str:
        self._cargar(config)

        if self._modelo is None:
            return ""

        voz = _config_voz(config)
        stt = voz.get("stt", {})
        idioma = str(stt.get("idioma", "es") or "es")

        try:
            segmentos, _info = self._modelo.transcribe(
                audio,
                language=idioma,
                beam_size=5,
                condition_on_previous_text=False,
                without_timestamps=True,
                vad_filter=True,
            )
            texto = "".join(segmento.text for segmento in segmentos).strip()
        except Exception:
            return ""

        return texto

    def _cargar(self, config: dict[str, Any] | None) -> None:
        if self._modelo is not None or self._error is not None:
            return

        try:
            WhisperModel = _importar_motor()
        except Exception as exc:
            self._error = exc
            return

        voz = _config_voz(config)
        stt = voz.get("stt", {})
        modelo = str(stt.get("modelo", "tiny") or "tiny")

        try:
            self._modelo = WhisperModel(modelo, device="cpu", compute_type="int8")
        except Exception as exc:
            self._error = exc


_motor_lock = threading.Lock()
_motor: FasterWhisperSTT | None = None


def _obtener_motor() -> FasterWhisperSTT:
    """Devuelve el motor compartido (una sola instancia por proceso)."""
    global _motor

    if _motor is None:
        with _motor_lock:
            if _motor is None:
                _motor = FasterWhisperSTT()

    return _motor


def _rms(bloque: Any, np: Any) -> float:
    """RMS de un bloque de audio. 0.0 si el bloque es nulo o vacio."""
    if bloque is None or getattr(bloque, "size", 0) == 0:
        return 0.0
    try:
        return float(np.sqrt(np.mean(bloque**2)))
    except Exception:
        return 0.0


def _estimar_suelo(ventana: list[float]) -> float:
    """Suelo de ruido estimado a partir del RMS reciente. 0.0 sin muestra."""
    if not ventana:
        return 0.0
    return float(median(ventana))


def _capturar_voz(
    flujo: Any,
    np: Any,
    max_duracion: float,
    silencio: float,
    reloj: Any | None = None,
) -> tuple[list[Any] | None, float, int]:
    """VAD adaptativo de dos fases sobre un flujo de audio.

    Fase 1 (espera): descarta bloques hasta detectar habla. El suelo de
    ruido se estima con el RMS reciente (mediana de la ventana) y el
    habla se dispara con `rms >= max(suelo * FACTOR_INICIO_HABLA,
    UMBRAL_INICIO_HABLA)`: un golpe de ruido puntual no activa la
    grabacion si no supera claramente el ambiente.

    Fase 2 (grabacion): acumula bloques usando histeresis (`rms >=
    suelo * FACTOR_HABLA` se mantiene habla) y termina tras `silencio`
    segundos por debajo del umbral, o al alcanzar `max_duracion`.

    Devuelve (bloques, suelo_de_ruido, bloques_habla). Devuelve None
    como bloques si no se detecto habla.
    """
    reloj = reloj or time.monotonic
    inicio_total = reloj()
    inicio_habla: float | None = None
    fase_espera = True
    bloques: list[Any] = []
    ventana: list[float] = []
    suelo = 0.0
    bloques_habla = 0
    silencioso_desde: float | None = None

    while True:
        ahora = reloj()

        if fase_espera:
            if ahora - inicio_total >= max_duracion:
                break
        elif ahora - inicio_habla >= max_duracion:
            break

        bloque, _desbordado = flujo.read(TAMANO_BLOQUE)
        rms = _rms(bloque, np)

        if fase_espera:
            if not ventana:
                ventana.append(rms)
                continue

            suelo = _estimar_suelo(ventana)
            umbral_inicio = max(suelo * FACTOR_INICIO_HABLA, UMBRAL_INICIO_HABLA)

            if rms >= umbral_inicio:
                fase_espera = False
                inicio_habla = ahora
                bloques.append(bloque)
                bloques_habla = 1
            else:
                ventana.append(rms)

                if len(ventana) > VENTANA_RUIDO:
                    ventana.pop(0)
            continue

        bloques.append(bloque)

        umbral_habla = max(suelo * FACTOR_HABLA, UMBRAL_SILENCIO)

        if rms >= umbral_habla:
            bloques_habla += 1
            silencioso_desde = None
        else:
            if silencioso_desde is None:
                silencioso_desde = ahora
            elif ahora - silencioso_desde >= silencio:
                break

    if fase_espera or not bloques:
        return None, suelo, 0

    return bloques, suelo, bloques_habla


def _capturar_bloques(
    flujo: Any,
    np: Any,
    max_duracion: float,
    silencio: float,
    reloj: Any | None = None,
) -> list[Any] | None:
    """Envoltorio compatible: VAD adaptativo que devuelve solo bloques."""
    bloques, _suelo, _n = _capturar_voz(
        flujo,
        np,
        max_duracion=max_duracion,
        silencio=silencio,
        reloj=reloj,
    )
    return bloques


def _bloques_habla_suficientes(bloques_habla: int) -> bool:
    """True si la captura tuvo al menos MIN_BLOQUES_HABLA de habla."""
    return bloques_habla >= MIN_BLOQUES_HABLA


def _es_audio_con_voz(audio: Any, suelo_ruido: float, np: Any) -> bool:
    """Puerta SNR: True si el pico supera el suelo de ruido con margen."""
    try:
        pico = float(np.max(np.abs(audio)))
    except Exception:
        return False

    return pico >= max(suelo_ruido * GANANCIA_SNR, UMBRAL_RECORTE)


def _aceptar_captura(
    bloques: list[Any],
    suelo_ruido: float,
    bloques_habla: int,
    np: Any,
) -> bool:
    """Gates de calidad sobre la captura: SNR + duracion minima de habla.

    Evita que ruido continuo o sonidos cortos del ambiente lleguen a
    Whisper. Se evalua sobre el audio sin normalizar (la normalizacion
    inflaria el pico y enmascararia la senal frente al ruido).
    """
    if not bloques:
        return False

    if not _bloques_habla_suficientes(bloques_habla):
        return False

    try:
        audio = np.concatenate(bloques).reshape(-1)
    except Exception:
        return False

    return _es_audio_con_voz(audio, suelo_ruido, np)


def _recortar_silencio(audio: Any, np: Any) -> Any | None:
    """Recorta el silencio de los bordes. None si el audio es puro silencio."""
    try:
        marcas = np.abs(audio) >= UMBRAL_RECORTE
        indices = np.flatnonzero(marcas)

        if indices.size == 0:
            return None

        inicio = int(indices[0])
        fin = int(indices[-1]) + 1
        return audio[inicio:fin]
    except Exception:
        return audio


def _normalizar_volumen(audio: Any, np: Any) -> Any:
    """Normaliza el pico del audio a 0.9 para una senal consistente."""
    try:
        pico = float(np.max(np.abs(audio)))
    except Exception:
        return audio

    if not pico or pico <= 0:
        return audio

    try:
        return audio * (0.9 / pico)
    except Exception:
        return audio


def _audio_desde_bloques(bloques: list[Any], np: Any) -> Any | None:
    """Concatena bloques, recorta silencio y normaliza. None si es silencio."""
    if not bloques:
        return None

    try:
        audio = np.concatenate(bloques).reshape(-1)
    except Exception:
        return None

    audio = _recortar_silencio(audio, np)

    if audio is None:
        return None

    return _normalizar_volumen(audio, np)


def _capturar_audio(config: dict[str, Any] | None) -> Any | None:
    """Captura audio del microfono y devuelve float32 mono a 16 kHz.

    Espera a que el usuario empiece a hablar, graba mientras habla y
    corta tras `silencio` segundos de silencio. Devuelve None si no
    se detecto habla o si falta el microfono/dependencias.
    """
    try:
        np, sd = _importar_captura()
    except Exception:
        return None

    voz = _config_voz(config)
    stt = voz.get("stt", {})
    max_duracion = float(stt.get("max_duracion_segundos", 6) or 6)
    silencio = float(stt.get("silencio_segundos", 0.6) or 0.6)

    try:
        with sd.InputStream(
            samplerate=RATE_MUESTREO,
            channels=1,
            dtype="float32",
        ) as flujo:
            bloques, suelo_ruido, bloques_habla = _capturar_voz(
                flujo,
                np,
                max_duracion=max_duracion,
                silencio=silencio,
            )
    except Exception:
        return None

    if not _aceptar_captura(bloques, suelo_ruido, bloques_habla, np):
        return None

    return _audio_desde_bloques(bloques, np)


def _normalizar_audio(audio: Any) -> Any:
    """Convierte bytes PCM16 o arrays a float32 mono a 16 kHz."""
    try:
        np, _sd = _importar_captura()
    except Exception:
        return audio

    if isinstance(audio, np.ndarray):
        if audio.dtype != np.float32:
            return audio.astype(np.float32)
        return audio

    if isinstance(audio, (bytes, bytearray)):
        muestras = np.frombuffer(bytes(audio), dtype=np.int16)
        return (muestras / 32768.0).astype(np.float32)

    return audio


def _es_esencialmente_silencio(audio: Any) -> bool:
    """True si el audio es nulo, vacio o su RMS esta bajo el umbral."""
    if audio is None or (hasattr(audio, "size") and audio.size == 0):
        return True

    try:
        np, _sd = _importar_captura()
        muestras = np.asarray(audio, dtype=np.float32)
        rms = float(np.sqrt(np.mean(muestras**2)))
        return rms < UMBRAL_SILENCIO
    except Exception:
        return False


def transcribir_audio(
    audio: Any | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """Transcribe audio del microfono (o el audio recibido) a texto.

    Devuelve "" si la voz esta desactivada, si falta el microfono, si
    falta una dependencia, si el audio es silencio o si el motor falla:
    ORION nunca se rompe.
    """
    if config is None:
        config = _config_por_defecto()

    if not stt_activada(config):
        return ""

    try:
        es_captura = audio is None

        if es_captura:
            audio = _capturar_audio(config)

        if audio is None:
            return ""

        audio = _normalizar_audio(audio)

        # El silencio capturado no se envia a Whisper: evita que el
        # modelo genere alucinaciones sobre audio que no tiene voz.
        if es_captura and _es_esencialmente_silencio(audio):
            return ""

        motor = _obtener_motor()
        return motor.transcribir(audio, config)
    except Exception:
        return ""


_PUNTUACION_BORDES = "¿¡?!.,;:…"
_FILLERS_VOZ = re.compile(
    r"^(?:"
    r"claro|vale|ok|okay|aja|ajá|jeje|jaja|ya|bueno|"
    r"mmm+|mhm+|hum+|hmm+|ah+|eh+|uh+|na"
    r")$"
)


def es_transcripcion_inutil(texto: str) -> bool:
    """Puerta de confianza de la entrada de voz.

    Devuelve True si la transcripcion es vacia, solo puntuacion, una
    muletilla corta ("claro", "vale", "ah", "mmm", "...") o un fragmento
    demasiado corto para ser una orden. Sirve para que main.py no envie
    ruido o confirmaciones sueltas al proveedor de IA.

    Solo se aplica a la entrada de voz: el modo teclado nunca pasa por
    aqui, por lo que no bloquea ordenes legitimas. "no" y "si" sueltos
    tambien se filtran porque en el bucle principal no hay pregunta
    pendiente (las confirmaciones se atienden por input()).
    """
    t = texto.lower()
    t = t.strip()
    t = t.strip(_PUNTUACION_BORDES)
    t = t.strip()

    if not t:
        return True

    if len(t) <= 2:
        return True

    return bool(_FILLERS_VOZ.fullmatch(t))


def precargar_motor(config: dict[str, Any] | None = None) -> bool:
    """Precarga el modelo STT reutilizando el singleton del proceso.

    Solo actua si voz.activada y voz.stt.activada son true. Devuelve
    True si el modelo quedo disponible, y False si la voz esta
    desactivada, si falta la extra de voz o si el modelo no cargo:
    ORION debe continuar por teclado en todos esos casos.
    """
    if config is None:
        config = _config_por_defecto()

    if not stt_activada(config):
        return False

    try:
        motor = _obtener_motor()
        motor._cargar(config)
        if motor._modelo is not None:
            _precalentar_vad()
        return motor._modelo is not None
    except Exception:
        return False