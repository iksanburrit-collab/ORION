"""TTS (Text-to-Speech) de ORION, desacoplado del core.

Motor por defecto: espeak via subprocess (ya presente en Linux).
No depende de pactl/paplay y no lanza excepciones hacia el resto.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any, Protocol


class TTSEngine(Protocol):
    """Contrato de un motor de voz sintetizada."""

    def hablar(self, texto: str, config: dict[str, Any] | None = None) -> None:
        ...


def _config_voz(config: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    voz = config.get("voz", {})
    return voz if isinstance(voz, dict) else {}


def tts_activada(config: dict[str, Any] | None) -> bool:
    voz = _config_voz(config)
    if not voz.get("activada", False):
        return False
    tts = voz.get("tts", {})
    return bool(tts.get("activada", False))


def _config_por_defecto() -> dict[str, Any] | None:
    """Carga la configuracion real de ORION. None si falla cualquier cosa."""
    try:
        from utilidades.configuracion import cargar_configuracion
        from utilidades.rutas import ruta_configuracion

        return cargar_configuracion(ruta_configuracion())
    except Exception:
        return None


def _ruta_espeak() -> str | None:
    try:
        return shutil.which("espeak")
    except Exception:
        return None


def _argumentos_espeak(config: dict[str, Any] | None, texto: str) -> list[str]:
    voz = _config_voz(config)
    tts = voz.get("tts", {})
    argumentos = [_ruta_espeak() or "espeak"]

    voz_id = tts.get("voz", "es")
    if voz_id:
        argumentos += ["-v", str(voz_id)]

    velocidad = tts.get("velocidad")
    if velocidad:
        argumentos += ["-s", str(velocidad)]

    argumentos.append(texto)
    return argumentos


def hablar(texto: str, config: dict[str, Any] | None = None) -> None:
    """Habla `texto`. No-op si la voz TTS esta desactivada o no hay espeak."""
    if config is None:
        config = _config_por_defecto()

    if not texto or not tts_activada(config):
        return

    if _ruta_espeak() is None:
        return

    try:
        subprocess.run(
            _argumentos_espeak(config, texto),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception:
        return