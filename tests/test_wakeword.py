import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from servicios.voz import wakeword as modulo_wakeword
from servicios.voz import listener as modulo_listener

try:
    import numpy as np

    _NUMPY = True
except ImportError:  # numpy no esta disponible sin la extra de voz
    np = None
    _NUMPY = False


_CONFIG = {
    "voz": {
        "activada": True,
        "stt": {
            "activada": True,
            "motor": "faster-whisper",
            "modelo": "tiny",
            "idioma": "es",
            "max_duracion_segundos": 6,
            "silencio_segundos": 0.6,
        },
        "tts": {
            "activada": True,
            "motor": "espeak",
            "voz": "es",
            "velocidad": 150,
        },
        "wakeword": {
            "activada": True,
            "motor": "openwakeword",
            "modelo": "hey_jarvis",
            "umbral": 0.5,
            "cooldown_segundos": 2.0,
        },
    }
}

_CONFIG_SIN_WAKEWORD = {
    "voz": {
        "activada": True,
        "stt": {"activada": True},
        "wakeword": {"activada": False},
    }
}

_CONFIG_SIN_VOZ = {
    "voz": {
        "activada": False,
        "stt": {"activada": False},
        "wakeword": {"activada": True},
    }
}


class WakeWordConfigTests(unittest.TestCase):
    def test_wakeword_activada_requiere_voz_y_wakeword(self):
        self.assertTrue(modulo_wakeword.wakeword_activada(_CONFIG))
        self.assertFalse(modulo_wakeword.wakeword_activada(_CONFIG_SIN_WAKEWORD))
        self.assertFalse(modulo_wakeword.wakeword_activada(_CONFIG_SIN_VOZ))
        self.assertFalse(modulo_wakeword.wakeword_activada(None))
        self.assertFalse(modulo_wakeword.wakeword_activada({"voz": "no-dict"}))

    def test_resolver_modelo_acepta_nombre_embebido(self):
        openwakeword = mock.Mock()
        openwakeword.models = {
            "hey_jarvis": {"model_path": "/ruta/hey_jarvis.onnx"},
        }
        ruta = modulo_wakeword._resolver_modelo("hey_jarvis", openwakeword)
        self.assertEqual(ruta, "/ruta/hey_jarvis.onnx")

    def test_resolver_modelo_acepta_ruta_onnx(self):
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".onnx") as archivo:
            ruta = modulo_wakeword._resolver_modelo(archivo.name, mock.Mock())
            self.assertEqual(ruta, archivo.name)

    def test_resolver_modelo_desconocido_devuelve_none(self):
        self.assertIsNone(modulo_wakeword._resolver_modelo("orion", mock.Mock()))
        self.assertIsNone(modulo_wakeword._resolver_modelo("", mock.Mock()))


class WakeWordDetectorTests(unittest.TestCase):
    def setUp(self):
        with modulo_wakeword._detector_lock:
            modulo_wakeword._detector = None

    def tearDown(self):
        with modulo_wakeword._detector_lock:
            modulo_wakeword._detector = None

    def _detector_cargado(self):
        detector = modulo_wakeword.WakeWordDetector()
        detector._modelo = mock.Mock()
        return detector

    def test_detector_sin_dependencia_no_carga(self):
        with mock.patch.object(
            modulo_wakeword,
            "_importar_openwakeword",
            side_effect=ImportError("openwakeword"),
        ):
            detector = modulo_wakeword.WakeWordDetector()
            detector._cargar(_CONFIG)
            self.assertFalse(detector.cargado())
            self.assertFalse(detector.procesar(np.zeros(1280) if _NUMPY else [0] * 1280))

    def test_detector_modelo_desconocido_no_carga(self):
        openwakeword = mock.Mock()
        openwakeword.models = {}
        with mock.patch.object(
            modulo_wakeword,
            "_importar_openwakeword",
            return_value=openwakeword,
        ):
            detector = modulo_wakeword.WakeWordDetector()
            detector._cargar(_CONFIG)
            self.assertFalse(detector.cargado())

    def test_detector_carga_y_activa_sobre_umbral(self):
        openwakeword = mock.Mock()
        openwakeword.models = {"hey_jarvis": {"model_path": "/ruta/m.onnx"}}
        modelo = mock.Mock()
        openwakeword.Model.return_value = modelo
        with mock.patch.object(
            modulo_wakeword,
            "_importar_openwakeword",
            return_value=openwakeword,
        ):
            detector = modulo_wakeword.WakeWordDetector()
            detector._cargar(_CONFIG)

        self.assertTrue(detector.cargado())

        modelo.predict.return_value = {"hey_jarvis_v0.1": 0.9}
        self.assertTrue(detector.procesar(np.zeros(1280) if _NUMPY else [0] * 1280))

        modelo.predict.return_value = {"hey_jarvis_v0.1": 0.3}
        self.assertFalse(detector.procesar(np.zeros(1280) if _NUMPY else [0] * 1280))

    def test_detector_en_cooldown_no_activa(self):
        detector = self._detector_cargado()
        detector._modelo.predict.return_value = {"hey_jarvis_v0.1": 0.9}

        detector.iniciar_cooldown()
        self.assertTrue(detector.en_cooldown())
        self.assertFalse(detector.procesar(np.zeros(1280) if _NUMPY else [0] * 1280))
        detector._modelo.predict.assert_not_called()

    def test_detector_reiniciar_sale_del_cooldown(self):
        detector = self._detector_cargado()
        detector.iniciar_cooldown()
        detector.reiniciar()
        self.assertFalse(detector.en_cooldown())

    def test_detector_error_de_predict_no_rompe(self):
        detector = self._detector_cargado()
        detector._modelo.predict.side_effect = RuntimeError("motor roto")
        self.assertFalse(detector.procesar(np.zeros(1280) if _NUMPY else [0] * 1280))

    def test_precargar_wakeword_reutiliza_el_singleton(self):
        detector = mock.Mock()
        detector.cargado.return_value = True
        with mock.patch.object(
            modulo_wakeword,
            "_obtener_detector",
            return_value=detector,
        ) as obtener:
            self.assertTrue(modulo_wakeword.precargar_wakeword(config=_CONFIG))
        obtener.assert_called_once_with()
        detector._cargar.assert_called_once_with(_CONFIG)

    def test_precargar_wakeword_desactivada_no_carga(self):
        with mock.patch.object(modulo_wakeword, "_obtener_detector") as obtener:
            self.assertFalse(modulo_wakeword.precargar_wakeword(config=_CONFIG_SIN_WAKEWORD))
        obtener.assert_not_called()

    def test_precargar_wakeword_devuelve_false_si_no_cargo(self):
        detector = mock.Mock()
        detector.cargado.return_value = False
        with mock.patch.object(
            modulo_wakeword,
            "_obtener_detector",
            return_value=detector,
        ):
            self.assertFalse(modulo_wakeword.precargar_wakeword(config=_CONFIG))

    def test_error_carga_configuracion_no_rompe(self):
        with mock.patch.object(modulo_wakeword, "_config_por_defecto", return_value=None):
            self.assertFalse(modulo_wakeword.precargar_wakeword())


class _DetectorFalso:
    """Detector falsificado para probar el listener sin microfono."""

    def __init__(self, tramos_hasta_activar=1):
        self._tramos = 0
        self._tramos_hasta_activar = tramos_hasta_activar
        self._cooldown = False
        self.cargado_llamado = False
        self.reinicios = 0

    def _cargar(self, config):
        self.cargado_llamado = True

    def cargado(self):
        return True

    def en_cooldown(self):
        return self._cooldown

    def iniciar_cooldown(self):
        self._cooldown = True

    def reiniciar(self):
        self.reinicios += 1
        self._cooldown = False

    def procesar(self, tramo):
        self._tramos += 1
        return self._tramos >= self._tramos_hasta_activar


class _FlujoWake:
    """Flujo que devuelve tramos predefinidos y luego bloquea el bucle."""

    def __init__(self, tramos, cola=None):
        self._tramos = list(tramos)
        self._cola = cola
        self._indice = 0

    def read(self, n):
        if self._indice < len(self._tramos):
            tramo = self._tramos[self._indice]
            self._indice += 1
            return tramo, False
        if self._cola is not None:
            return self._cola(), False
        raise RuntimeError("FlujoWake sin mas tramos.")


@unittest.skipUnless(_NUMPY, "numpy no instalado (extra de voz)")
class ListenerTests(unittest.TestCase):
    def setUp(self):
        with modulo_wakeword._detector_lock:
            modulo_wakeword._detector = None

    def tearDown(self):
        with modulo_wakeword._detector_lock:
            modulo_wakeword._detector = None

    def _entorno(self, flujo):
        sd = mock.MagicMock()
        sd.InputStream.return_value.__enter__.return_value = flujo
        return sd

    def test_bucle_escucha_no_abre_stream_si_wakeword_desactivada(self):
        with (
            mock.patch.object(modulo_listener, "_importar_captura") as importar,
            mock.patch.object(modulo_listener, "_obtener_detector") as obtener,
        ):
            modulo_listener.bucle_escucha(_CONFIG_SIN_WAKEWORD)
        importar.assert_not_called()
        obtener.assert_not_called()

    def test_bucle_escucha_no_abre_stream_si_modelo_no_cargo(self):
        detector = mock.Mock()
        detector.cargado.return_value = False
        with (
            mock.patch.object(modulo_listener, "_obtener_detector", return_value=detector),
            mock.patch.object(modulo_listener, "_importar_captura") as importar,
        ):
            modulo_listener.bucle_escucha(_CONFIG)
        importar.assert_not_called()

    def test_bucle_escucha_transcribe_y_llama_al_callback(self):
        tramo = np.zeros((modulo_wakeword.TAMANO_TRAMO, 1), dtype=np.float32)
        flujo = _FlujoWake([tramo, tramo, tramo])
        sd = self._entorno(flujo)
        detector = _DetectorFalso(tramos_hasta_activar=1)

        recibidos = []

        with (
            mock.patch.object(
                modulo_listener,
                "_importar_captura",
                return_value=(np, sd),
            ),
            mock.patch.object(modulo_listener, "_obtener_detector", return_value=detector),
            mock.patch.object(
                modulo_listener,
                "_capturar_y_transcribir",
                return_value="qué hora es",
            ) as transcribir,
        ):
            modulo_listener.bucle_escucha(
                _CONFIG,
                al_recibir_texto=lambda texto: recibidos.append(texto) or False,
            )

        self.assertEqual(recibidos, ["qué hora es"])
        transcribir.assert_called_once()

    def test_bucle_escucha_ignora_transcripcion_inutil(self):
        tramo = np.zeros((modulo_wakeword.TAMANO_TRAMO, 1), dtype=np.float32)
        flujo = _FlujoWake([tramo, tramo, tramo])
        sd = self._entorno(flujo)
        detector = _DetectorFalso(tramos_hasta_activar=1)

        recibidos = []

        with (
            mock.patch.object(
                modulo_listener,
                "_importar_captura",
                return_value=(np, sd),
            ),
            mock.patch.object(modulo_listener, "_obtener_detector", return_value=detector),
            mock.patch.object(modulo_listener, "_capturar_y_transcribir", return_value="vale"),
        ):
            # "vale" es una muletilla: no llega al callback y el bucle
            # vuelve a ESPERA (el flujo se agota y termina en silencio).
            modulo_listener.bucle_escucha(
                _CONFIG,
                al_recibir_texto=lambda texto: recibidos.append(texto) or False,
            )

        self.assertEqual(recibidos, [])

    def test_bucle_escucha_callback_false_termina(self):
        tramo = np.zeros((modulo_wakeword.TAMANO_TRAMO, 1), dtype=np.float32)
        flujo = _FlujoWake([tramo, tramo, tramo])
        sd = self._entorno(flujo)
        detector = _DetectorFalso(tramos_hasta_activar=1)

        with (
            mock.patch.object(
                modulo_listener,
                "_importar_captura",
                return_value=(np, sd),
            ),
            mock.patch.object(modulo_listener, "_obtener_detector", return_value=detector),
            mock.patch.object(
                modulo_listener,
                "_capturar_y_transcribir",
                return_value="salir",
            ),
        ):
            modulo_listener.bucle_escucha(_CONFIG, al_recibir_texto=lambda texto: False)

        self.assertEqual(detector._tramos, 1)


if __name__ == "__main__":
    unittest.main()