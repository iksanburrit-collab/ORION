import copy
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib import error


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.memoria import inicializar_memoria
from ia.ollama import ERROR_OLLAMA, generar_respuesta
from ia.proveedor import RespuestaProveedor


class RespuestaHTTPFalsa:
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.cuerpo


class IntegracionOllamaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {
            "modo": "normal",
            "ia": {
                "activada": True,
                "modelo": "qwen3:1.7b",
                "timeout": 60,
                "limite_contexto": 1200,
            },
        }

    def tearDown(self):
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    @mock.patch("ia.ollama.request.urlopen")
    def test_payload_correcto_y_extrae_message_content(self, urlopen):
        urlopen.return_value = RespuestaHTTPFalsa(
            b'{"message":{"content":"Hola, soy ORION.","thinking":"oculto"}}'
        )

        respuesta = generar_respuesta(
            "hola",
            contexto="Perfil: nombre Michel",
            modelo="qwen3:1.7b",
            timeout=12,
        )
        solicitud = urlopen.call_args.args[0]
        payload = json.loads(solicitud.data.decode("utf-8"))

        self.assertEqual(respuesta, "Hola, soy ORION.")
        self.assertEqual(payload["model"], "qwen3:1.7b")
        self.assertFalse(payload["think"])
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["keep_alive"], "10m")
        self.assertEqual(payload["options"]["num_predict"], 100)
        self.assertEqual(payload["options"]["num_ctx"], 2048)
        self.assertIn("Perfil: nombre Michel", payload["messages"][0]["content"])
        self.assertEqual(payload["messages"][-1]["content"], "hola")
        self.assertNotIn("oculto", respuesta)

    @mock.patch("ia.ollama.request.urlopen")
    def test_error_ollama_no_disponible(self, urlopen):
        urlopen.side_effect = error.URLError("connection refused")

        respuesta = generar_respuesta("hola")

        self.assertTrue(respuesta.startswith(ERROR_OLLAMA))
        self.assertIn("conectar", respuesta)

    @mock.patch("ia.ollama.request.urlopen")
    def test_timeout(self, urlopen):
        urlopen.side_effect = socket.timeout()

        respuesta = generar_respuesta("hola", timeout=0.1)

        self.assertTrue(respuesta.startswith(ERROR_OLLAMA))
        self.assertIn("demasiado", respuesta)

    @mock.patch("ia.ollama.request.urlopen")
    def test_respuesta_vacia(self, urlopen):
        urlopen.return_value = RespuestaHTTPFalsa(b'{"message":{"content":""}}')

        respuesta = generar_respuesta("hola")

        self.assertTrue(respuesta.startswith(ERROR_OLLAMA))
        self.assertIn("vacia", respuesta)

    @mock.patch("ia.ollama.request.urlopen")
    def test_json_invalido(self, urlopen):
        urlopen.return_value = RespuestaHTTPFalsa(b"no es json")

        respuesta = generar_respuesta("hola")

        self.assertTrue(respuesta.startswith(ERROR_OLLAMA))
        self.assertIn("JSON invalido", respuesta)

    @mock.patch("core.cerebro.generar_respuesta")
    def test_comando_conocido_no_llama_a_ollama(self, generar):
        resultado = procesar("hora", self.memoria, self.config)

        generar.assert_not_called()
        self.assertEqual(resultado.accion, "mostrar_hora")

    @mock.patch("core.cerebro.generar_respuesta")
    def test_mensaje_desconocido_llama_a_ollama_y_usa_contexto(
        self,
        generar,
    ):
        generar.return_value = RespuestaProveedor("Respuesta local", "ollama")

        resultado = procesar("cuentame algo de automatizacion", self.memoria, self.config)

        self.assertEqual(resultado.accion, "respuesta_ia_ollama")
        generar.assert_called_once_with(
            "cuentame algo de automatizacion",
            self.memoria,
            self.config,
            historial=[],
        )

    @mock.patch("core.cerebro.generar_respuesta")
    def test_ia_desactivada_usa_respuesta_desconocida_normal(self, generar):
        self.config["ia"]["activada"] = False

        resultado = procesar("frase sin comando", self.memoria, self.config)

        generar.assert_not_called()
        self.assertEqual(resultado.accion, "desconocido")

    @mock.patch("core.cerebro.generar_respuesta")
    def test_ia_no_modifica_memoria_personal(self, generar):
        generar.return_value = RespuestaProveedor("Respuesta local", "ollama")
        usuario_antes = copy.deepcopy(self.memoria["usuario"])
        aprendizaje_antes = copy.deepcopy(self.memoria["aprendizaje"])

        procesar("conversemos un rato", self.memoria, self.config)

        self.assertEqual(self.memoria["usuario"], usuario_antes)
        self.assertEqual(self.memoria["aprendizaje"], aprendizaje_antes)
        self.assertEqual(len(self.memoria["conversacion"]), 1)


if __name__ == "__main__":
    unittest.main()
