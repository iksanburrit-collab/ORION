import builtins
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import main
from servicios.voz import hablar, transcribir_audio
from servicios.voz import stt as modulo_stt
from servicios.voz import tts as modulo_tts
from utilidades.archivos import guardar_json
from utilidades.configuracion import CONFIG_PREDETERMINADA, cargar_configuracion
from utilidades.rutas import configurar_base_datos, ruta_configuracion

try:
    import numpy as np

    _NUMPY = True
except ImportError:  # numpy no esta disponible sin la extra de voz
    np = None
    _NUMPY = False


class _FlujoFalso:
    """Flujo de audio falsificado para probar el VAD sin microfono."""

    def __init__(self, bloques, cola=None):
        self._bloques = list(bloques)
        self._cola = cola
        self._indice = 0

    def read(self, n):
        if self._indice < len(self._bloques):
            bloque = self._bloques[self._indice]
            self._indice += 1
            return bloque, False
        if self._cola is not None:
            return self._cola(), False
        raise RuntimeError("FlujoFalso sin mas bloques.")


_CONFIG = {
    "voz": {
        "activada": True,
        "stt": {
            "activada": True,
            "motor": "faster-whisper",
            "modelo": "tiny",
            "idioma": "es",
        },
        "tts": {
            "activada": True,
            "motor": "espeak",
            "voz": "es",
            "velocidad": 150,
        },
    }
}

_CONFIG_SIN_VOZ = {
    "voz": {
        "activada": False,
        "stt": {"activada": False},
        "tts": {"activada": False},
    }
}


class VozSTTTests(unittest.TestCase):
    def setUp(self):
        self._reinicar_motor()

    def tearDown(self):
        self._reinicar_motor()

    def _reinicar_motor(self):
        with modulo_stt._motor_lock:
            modulo_stt._motor = None

    def test_voz_desactivada_devuelve_vacio_sin_capturar(self):
        with mock.patch.object(modulo_stt, "_capturar_audio") as captura:
            self.assertEqual(transcribir_audio(config=_CONFIG_SIN_VOZ), "")
        captura.assert_not_called()

    def test_stt_sin_dependencia_devuelve_vacio(self):
        with (
            mock.patch.object(modulo_stt, "_capturar_audio", return_value=b"\x00\x00"),
            mock.patch.object(modulo_stt, "_importar_captura", side_effect=ImportError("numpy")),
            mock.patch.object(modulo_stt, "_importar_motor", side_effect=ImportError("faster-whisper")),
        ):
            self.assertEqual(transcribir_audio(config=_CONFIG), "")

    def test_stt_motor_fallando_devuelve_vacio(self):
        with (
            mock.patch.object(modulo_stt, "_capturar_audio", return_value=b"\x00\x00"),
            mock.patch.object(modulo_stt, "_importar_captura", side_effect=ImportError("numpy")),
        ):
            motor = mock.Mock()
            motor.transcribir.side_effect = RuntimeError("motor roto")
            with mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor):
                self.assertEqual(transcribir_audio(config=_CONFIG), "")

    def test_stt_sin_voz_devuelve_vacio(self):
        with mock.patch.object(modulo_stt, "_capturar_audio", return_value=None):
            self.assertEqual(transcribir_audio(config=_CONFIG), "")

    def test_stt_motor_devuelve_texto(self):
        with (
            mock.patch.object(modulo_stt, "_capturar_audio", return_value=b"\x00\x00"),
            mock.patch.object(modulo_stt, "_importar_captura", side_effect=ImportError("numpy")),
        ):
            motor = mock.Mock()
            motor.transcribir.return_value = "abre firefox"
            with mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor):
                self.assertEqual(transcribir_audio(config=_CONFIG), "abre firefox")

    def test_transcribir_sin_config_carga_configuracion(self):
        with tempfile.TemporaryDirectory() as tmp:
            configurar_base_datos(tmp)
            try:
                guardar_json(
                    ruta_configuracion(),
                    {
                        "voz": {
                            "activada": True,
                            "stt": {
                                "activada": True,
                                "motor": "faster-whisper",
                                "modelo": "tiny",
                                "idioma": "es",
                            },
                        }
                    },
                )
                with (
                    mock.patch.object(modulo_stt, "_capturar_audio", return_value=b"\x00\x00"),
                    mock.patch.object(modulo_stt, "_importar_captura", side_effect=ImportError("numpy")),
                ):
                    motor = mock.Mock()
                    motor.transcribir.return_value = "abre firefox"
                    with mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor):
                        self.assertEqual(transcribir_audio(), "abre firefox")
            finally:
                configurar_base_datos(None)

    def test_config_explicita_stt_no_usa_por_defecto(self):
        with (
            mock.patch.object(modulo_stt, "_config_por_defecto") as por_defecto,
            mock.patch.object(modulo_stt, "_capturar_audio", return_value=b"\x00\x00"),
            mock.patch.object(modulo_stt, "_importar_captura", side_effect=ImportError("numpy")),
        ):
            motor = mock.Mock()
            motor.transcribir.return_value = "abre firefox"
            with mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor):
                self.assertEqual(transcribir_audio(config=_CONFIG), "abre firefox")
        por_defecto.assert_not_called()

    def test_error_carga_configuracion_stt_no_rompe(self):
        with mock.patch.object(modulo_stt, "_config_por_defecto", return_value=None):
            self.assertEqual(transcribir_audio(), "")

    def test_error_al_cargar_configuracion_devuelve_none(self):
        with mock.patch(
            "utilidades.configuracion.cargar_configuracion",
            side_effect=OSError("boom"),
        ):
            self.assertIsNone(modulo_stt._config_por_defecto())
            self.assertIsNone(modulo_tts._config_por_defecto())

    def test_precarga_reutiliza_el_singleton(self):
        motor = mock.Mock()
        motor._modelo = object()
        with mock.patch.object(
            modulo_stt,
            "_obtener_motor",
            return_value=motor,
        ) as obtener:
            self.assertTrue(modulo_stt.precargar_motor(config=_CONFIG))

        obtener.assert_called_once()
        motor._cargar.assert_called_once_with(_CONFIG)

    def test_precarga_devuelve_false_si_modelo_no_cargo(self):
        motor = mock.Mock()
        motor._modelo = None
        with mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor):
            self.assertFalse(modulo_stt.precargar_motor(config=_CONFIG))

    def test_precarga_no_activa_si_voz_desactivada(self):
        with mock.patch.object(modulo_stt, "_obtener_motor") as obtener:
            self.assertFalse(modulo_stt.precargar_motor(config=_CONFIG_SIN_VOZ))
        obtener.assert_not_called()

    def test_precarga_no_rompe_sin_faster_whisper(self):
        motor = modulo_stt.FasterWhisperSTT()
        with (
            mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor),
            mock.patch.object(
                modulo_stt,
                "_importar_motor",
                side_effect=ImportError("faster-whisper"),
            ),
        ):
            self.assertFalse(modulo_stt.precargar_motor(config=_CONFIG))

    def test_precarga_precalienta_el_vad(self):
        motor = mock.Mock()
        motor._modelo = object()
        with (
            mock.patch.object(modulo_stt, "_precalentar_vad") as precalentar,
            mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor),
        ):
            self.assertTrue(modulo_stt.precargar_motor(config=_CONFIG))
        precalentar.assert_called_once_with()

    def test_precarga_no_precalienta_vad_si_modelo_no_cargo(self):
        motor = mock.Mock()
        motor._modelo = None
        with (
            mock.patch.object(modulo_stt, "_precalentar_vad") as precalentar,
            mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor),
        ):
            self.assertFalse(modulo_stt.precargar_motor(config=_CONFIG))
        precalentar.assert_not_called()

    def test_precalentar_vad_carga_el_modelo_silero(self):
        with mock.patch(
            "faster_whisper.vad.get_vad_model",
            return_value=object(),
        ) as get_vad:
            self.assertIsNone(modulo_stt._precalentar_vad())
        get_vad.assert_called_once()

    def test_precalentar_vad_no_rompe_si_falta_dependencia(self):
        with mock.patch.dict(sys.modules, {"faster_whisper.vad": None}):
            self.assertIsNone(modulo_stt._precalentar_vad())

    def test_transcripcion_inutil_vacia_o_solo_puntuacion(self):
        for texto in ("", "   ", "...", "?!", ",,,"):
            with self.subTest(texto=texto):
                self.assertTrue(modulo_stt.es_transcripcion_inutil(texto))

    def test_transcripcion_inutil_muletillas(self):
        for texto in ("claro", "vale", "ah", "mmm", "mhm", "ok", "aja", "jeje"):
            with self.subTest(texto=texto):
                self.assertTrue(modulo_stt.es_transcripcion_inutil(texto))

    def test_transcripcion_inutil_fragmentos_cortos(self):
        for texto in ("no", "si", "sí", "ya", "eh"):
            with self.subTest(texto=texto):
                self.assertTrue(modulo_stt.es_transcripcion_inutil(texto))

    def test_transcripcion_util_no_se_bloquea(self):
        for texto in (
            "abre firefox",
            "qué hora es",
            "hora",
            "fecha",
            "salir",
            "2 + 2",
            "crea una nota",
            "hola orion",
        ):
            with self.subTest(texto=texto):
                self.assertFalse(modulo_stt.es_transcripcion_inutil(texto))


@unittest.skipUnless(_NUMPY, "numpy no instalado (extra de voz)")
class VozCapturaTests(unittest.TestCase):
    """Tests del VAD de dos fases y del preprocesamiento de la captura."""

    def setUp(self):
        with modulo_stt._motor_lock:
            modulo_stt._motor = None

    def tearDown(self):
        with modulo_stt._motor_lock:
            modulo_stt._motor = None

    def _silencioso(self):
        return np.zeros((modulo_stt.TAMANO_BLOQUE, 1), dtype=np.float32)

    def _habla(self, amplitud=0.3):
        return np.full(
            (modulo_stt.TAMANO_BLOQUE, 1),
            amplitud,
            dtype=np.float32,
        )

    def _ruido(self, amplitud=0.03):
        return np.full(
            (modulo_stt.TAMANO_BLOQUE, 1),
            amplitud,
            dtype=np.float32,
        )

    def _capturar_con_reloj(self, reloj, bloques, max_duracion, silencio=0.6, cola=None):
        return modulo_stt._capturar_bloques(
            _FlujoFalso(bloques, cola),
            np,
            max_duracion=max_duracion,
            silencio=silencio,
            reloj=iter(reloj).__next__,
        )

    def _capturar_voz_con_reloj(self, reloj, bloques, max_duracion, silencio=0.6, cola=None):
        return modulo_stt._capturar_voz(
            _FlujoFalso(bloques, cola),
            np,
            max_duracion=max_duracion,
            silencio=silencio,
            reloj=iter(reloj).__next__,
        )

    def test_ruido_continuo_no_activa_la_captura(self):
        ruido = self._ruido(0.03)
        bloques, suelo, n_habla = self._capturar_voz_con_reloj(
            [0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            [ruido] * 6,
            max_duracion=0.5,
        )
        self.assertIsNone(bloques)
        self.assertGreaterEqual(suelo, 0.02)
        self.assertEqual(n_habla, 0)

    def test_vad_adaptativo_detecta_inicio_de_voz(self):
        q = self._ruido(0.005)
        sp = self._habla(0.3)
        s = self._silencioso()
        bloques = [q, q, q, sp, sp, s, s, s, s, s, s, s]
        reloj = [0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1]

        resultado, suelo, n_habla = self._capturar_voz_con_reloj(
            reloj,
            bloques,
            max_duracion=6.0,
        )

        self.assertIsNotNone(resultado)
        self.assertEqual(len(resultado), 9)
        self.assertEqual(n_habla, 2)
        self.assertLess(suelo, 0.01)

    def test_vad_adaptativo_detecta_fin_de_voz(self):
        n = self._ruido(0.02)
        sp = self._habla(0.4)
        bloques = [n, n, n, sp, sp, sp, n, n, n, n, n, n, n]
        reloj = [
            0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5,
            0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2,
        ]

        resultado, suelo, n_habla = self._capturar_voz_con_reloj(
            reloj,
            bloques,
            max_duracion=6.0,
        )

        self.assertIsNotNone(resultado)
        self.assertEqual(len(resultado), 10)
        self.assertEqual(n_habla, 3)
        self.assertTrue(modulo_stt._bloques_habla_suficientes(n_habla))
        self.assertTrue(modulo_stt._aceptar_captura(resultado, suelo, n_habla, np))

    def test_ruido_fuerte_aislado_no_genera_transcripcion(self):
        q = self._ruido(0.005)
        golpe = self._habla(0.4)
        s = self._silencioso()
        bloques = [q, q, golpe, s, s, s, s, s, s, s, s, s]
        reloj = [0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

        resultado, suelo, n_habla = self._capturar_voz_con_reloj(
            reloj,
            bloques,
            max_duracion=6.0,
        )

        self.assertIsNotNone(resultado)
        self.assertEqual(n_habla, 1)
        self.assertFalse(modulo_stt._bloques_habla_suficientes(n_habla))
        self.assertFalse(modulo_stt._aceptar_captura(resultado, suelo, n_habla, np))

    def test_puerta_snr_rechaza_senal_sin_margen(self):
        senal = np.full((8000,), 0.1, dtype=np.float32)
        self.assertTrue(modulo_stt._es_audio_con_voz(senal, 0.005, np))
        self.assertFalse(modulo_stt._es_audio_con_voz(senal, 0.04, np))

    def test_vad_filter_se_envia_al_motor(self):
        motor = modulo_stt.FasterWhisperSTT()
        motor._modelo = mock.Mock()
        with mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor):
            transcribir_audio(audio=b"\x00\x00", config=_CONFIG)

        motor._modelo.transcribe.assert_called_once()
        self.assertTrue(motor._modelo.transcribe.call_args.kwargs["vad_filter"])

    def test_silencio_puro_no_genera_transcripcion_falsa(self):
        sil = self._silencioso()
        bloques = self._capturar_con_reloj(
            [0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            [sil, sil, sil],
            max_duracion=0.5,
            cola=lambda: self._silencioso(),
        )
        self.assertIsNone(bloques)

        self.assertIsNone(modulo_stt._recortar_silencio(sil.reshape(-1), np))

    def test_silencio_capturado_no_va_a_whisper(self):
        sil = np.zeros((1600,), dtype=np.float32)
        motor = mock.Mock()
        with (
            mock.patch.object(modulo_stt, "_capturar_audio", return_value=sil),
            mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor),
        ):
            self.assertEqual(transcribir_audio(config=_CONFIG), "")
        motor.transcribir.assert_not_called()

    def test_frase_corta_valida_se_conserva(self):
        sil = self._silencioso()
        habla = self._habla()
        audio = modulo_stt._audio_desde_bloques([sil, habla, habla, sil], np)

        self.assertIsNotNone(audio)
        self.assertEqual(audio.size, 2 * modulo_stt.TAMANO_BLOQUE)
        self.assertTrue(np.isclose(np.max(np.abs(audio)), 0.9))

    def test_detector_termina_despues_del_silencio_configurado(self):
        sil = self._silencioso()
        habla = self._habla()
        bloques = [sil, habla, habla, habla, sil, sil, sil, sil, sil, sil, sil, sil]
        reloj = [0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

        resultado = self._capturar_con_reloj(
            reloj,
            bloques,
            max_duracion=6.0,
            silencio=0.6,
        )

        self.assertEqual(len(resultado), 10)

    def test_timeout_maximo_sigue_funcionando(self):
        sil = self._silencioso()
        bloques = self._capturar_con_reloj(
            [0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            [sil, sil, sil, sil, sil],
            max_duracion=0.5,
            cola=lambda: self._silencioso(),
        )
        self.assertIsNone(bloques)

    def test_audio_proporcionado_directamente_no_se_rompe(self):
        motor = mock.Mock()
        motor.transcribir.return_value = "abre firefox"
        with mock.patch.object(modulo_stt, "_obtener_motor", return_value=motor):
            self.assertEqual(
                transcribir_audio(audio=b"\x00\x00", config=_CONFIG),
                "abre firefox",
            )


class VozTTSTests(unittest.TestCase):
    def test_tts_desactivado_no_ejecuta(self):
        with mock.patch.object(modulo_tts.subprocess, "run") as correr:
            hablar("hola", config=_CONFIG_SIN_VOZ)
        correr.assert_not_called()

    def test_tts_sin_espeak_no_op(self):
        with (
            mock.patch.object(modulo_tts.shutil, "which", return_value=None),
            mock.patch.object(modulo_tts.subprocess, "run") as correr,
        ):
            hablar("hola", config=_CONFIG)
        correr.assert_not_called()

    def test_tts_usa_espeak(self):
        with (
            mock.patch.object(modulo_tts.shutil, "which", return_value="/usr/bin/espeak"),
            mock.patch.object(modulo_tts.subprocess, "run") as correr,
        ):
            hablar("hola", config=_CONFIG)
        correr.assert_called_once()
        argumentos = correr.call_args.args[0]
        self.assertEqual(argumentos[0], "/usr/bin/espeak")
        self.assertEqual(argumentos[-1], "hola")

    def test_tts_error_espeak_no_propaga(self):
        with (
            mock.patch.object(modulo_tts.shutil, "which", return_value="/usr/bin/espeak"),
            mock.patch.object(modulo_tts.subprocess, "run", side_effect=OSError("boom")),
        ):
            hablar("hola", config=_CONFIG)  # no debe lanzar

    def test_hablar_sin_config_carga_configuracion(self):
        with tempfile.TemporaryDirectory() as tmp:
            configurar_base_datos(tmp)
            try:
                guardar_json(
                    ruta_configuracion(),
                    {
                        "voz": {
                            "activada": True,
                            "tts": {
                                "activada": True,
                                "motor": "espeak",
                                "voz": "es",
                                "velocidad": 150,
                            },
                        }
                    },
                )
                with (
                    mock.patch.object(modulo_tts.shutil, "which", return_value="/usr/bin/espeak"),
                    mock.patch.object(modulo_tts.subprocess, "run") as correr,
                ):
                    hablar("hola")
            finally:
                configurar_base_datos(None)
        correr.assert_called_once()

    def test_config_explicita_tts_no_usa_por_defecto(self):
        with (
            mock.patch.object(modulo_tts, "_config_por_defecto") as por_defecto,
            mock.patch.object(modulo_tts.shutil, "which", return_value="/usr/bin/espeak"),
            mock.patch.object(modulo_tts.subprocess, "run") as correr,
        ):
            hablar("hola", config=_CONFIG)
        por_defecto.assert_not_called()
        correr.assert_called_once()

    def test_error_carga_configuracion_tts_no_rompe(self):
        with mock.patch.object(modulo_tts, "_config_por_defecto", return_value=None):
            hablar("hola")  # no debe lanzar


class MainVozTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def test_main_conserva_input_cuando_voz_desactivada(self):
        salida = io.StringIO()
        with mock.patch.object(sys, "stdout", salida), mock.patch.object(
            builtins,
            "input",
            return_value="salir",
        ) as entrada:
            main.ejecutar()

        entrada.assert_called_once_with("\nORION> ")
        self.assertIn("Apagando ORION", salida.getvalue())

    def test_main_descarta_transcripcion_voz_inutil(self):
        salida = io.StringIO()

        def resultado_fake(*args, **kwargs):
            texto = kwargs.get("texto") or (args[0] if args else "")
            return mock.Mock(
                texto=texto,
                respuesta="",
                salir=(texto == "salir"),
                solicitud=None,
                solicitud_pendiente=None,
                debug=None,
            )

        with (
            mock.patch.object(sys, "stdout", salida),
            mock.patch.object(
                main,
                "transcribir_audio",
                side_effect=["vale", ""],
            ),
            mock.patch.object(main, "procesar", side_effect=resultado_fake) as procesar,
            mock.patch.object(
                builtins,
                "input",
                return_value="salir",
            ),
        ):
            main.ejecutar()

        # "vale" se descarta sin llegar al cerebro; solo se procesa "salir".
        procesar.assert_called_once()
        self.assertEqual(procesar.call_args.args[0], "salir")

    def test_main_teclado_no_pasa_por_la_puerta_de_voz(self):
        salida = io.StringIO()

        def resultado_fake(*args, **kwargs):
            texto = kwargs.get("texto") or (args[0] if args else "")
            return mock.Mock(
                texto=texto,
                respuesta="",
                salir=(texto == "salir"),
                solicitud=None,
                solicitud_pendiente=None,
                debug=None,
            )

        with (
            mock.patch.object(sys, "stdout", salida),
            mock.patch.object(main, "transcribir_audio", return_value=""),
            mock.patch.object(main, "procesar", side_effect=resultado_fake) as procesar,
            mock.patch.object(
                builtins,
                "input",
                side_effect=["vale", "salir"],
            ),
        ):
            main.ejecutar()

        # El teclado no se filtra: "vale" escrito si llega al cerebro.
        self.assertEqual(procesar.call_count, 2)


class ConfigVozTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def test_configuracion_incluye_voz_sin_romper_existente(self):
        config = cargar_configuracion()

        self.assertEqual(config["voz"], CONFIG_PREDETERMINADA["voz"])
        self.assertFalse(config["voz"]["activada"])
        self.assertEqual(config["voz"]["stt"]["motor"], "faster-whisper")
        self.assertEqual(config["voz"]["stt"]["modelo"], "tiny")
        self.assertEqual(config["voz"]["tts"]["motor"], "espeak")
        self.assertIn("ia", config)
        self.assertIn("sistema", config)


if __name__ == "__main__":
    unittest.main()