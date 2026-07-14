import io
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
from core.intenciones import detectar_intencion
from core.memoria import VERSION_MEMORIA, inicializar_memoria
from ia.nvidia import (
    ERROR_NVIDIA,
    NVIDIA_URL,
    DiagnosticoNvidia,
    generar_respuesta_nvidia,
    generar_respuesta_nvidia_diagnostico,
)
from ia.proveedor import generar_respuesta


class RespuestaHTTPFalsa:
    def __init__(self, cuerpo, status=200):
        self.cuerpo = cuerpo
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.cuerpo

    def getcode(self):
        return self.status


class ProveedorHibridoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {
            "modo": "normal",
            "ia": {
                "activada": True,
                "proveedor": "nvidia",
                "fallback_local": True,
                "limite_contexto": 900,
                "max_turnos": 4,
                "nvidia": {
                    "modelo": "meta/llama-4-maverick-17b-128e-instruct",
                    "timeout": 25,
                    "max_tokens": 180,
                },
                "ollama": {
                    "modelo": "qwen3:1.7b",
                    "timeout": 60,
                    "keep_alive": "10m",
                    "num_predict": 100,
                    "num_ctx": 2048,
                },
            },
        }

    def tearDown(self):
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    @mock.patch.dict(os.environ, {"NVIDIA_API_KEY": "clave-prueba"})
    @mock.patch("ia.nvidia.request.urlopen")
    def test_payload_nvidia_correcto_y_extrae_content(self, urlopen):
        urlopen.return_value = RespuestaHTTPFalsa(
            b'{"choices":[{"message":{"content":"Respuesta NVIDIA"}}]}'
        )

        respuesta = generar_respuesta_nvidia(
            "hola",
            contexto="Perfil: nombre Michel",
            timeout=7,
        )
        solicitud = urlopen.call_args.args[0]
        payload = json.loads(solicitud.data.decode("utf-8"))

        self.assertEqual(respuesta, "Respuesta NVIDIA")
        self.assertEqual(solicitud.full_url, NVIDIA_URL)
        self.assertEqual(
            payload["model"],
            "meta/llama-4-maverick-17b-128e-instruct",
        )
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["max_tokens"], 180)
        self.assertIn("Bearer ", solicitud.headers["Authorization"])
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 7)
        self.assertNotIn("clave-prueba", respuesta)

    @mock.patch.dict(os.environ, {"NVIDIA_API_KEY": "clave-prueba"})
    @mock.patch("ia.nvidia.request.urlopen")
    def test_diagnostico_nvidia_incluye_http_y_tiempo(self, urlopen):
        urlopen.return_value = RespuestaHTTPFalsa(
            b'{"choices":[{"message":{"content":"Respuesta NVIDIA"}}]}'
        )

        diagnostico = generar_respuesta_nvidia_diagnostico("hola", timeout=3)

        self.assertEqual(diagnostico.http, 200)
        self.assertEqual(diagnostico.mensaje, "OK")
        self.assertEqual(diagnostico.endpoint, NVIDIA_URL)
        self.assertTrue(diagnostico.api_detectada)
        self.assertEqual(diagnostico.timeout, 3)
        self.assertEqual(diagnostico.texto, "Respuesta NVIDIA")

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_nvidia_api_key_ausente(self):
        respuesta = generar_respuesta_nvidia("hola")

        self.assertTrue(respuesta.startswith(ERROR_NVIDIA))
        self.assertIn("NVIDIA_API_KEY", respuesta)

    @mock.patch.dict(os.environ, {"NVIDIA_API_KEY": "clave-prueba"})
    @mock.patch("ia.nvidia.request.urlopen")
    def test_nvidia_http_401_y_429(self, urlopen):
        urlopen.side_effect = error.HTTPError(
            NVIDIA_URL,
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"secret"}'),
        )

        self.assertIn("credenciales", generar_respuesta_nvidia("hola"))

        urlopen.side_effect = error.HTTPError(
            NVIDIA_URL,
            429,
            "Rate limit",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"secret"}'),
        )

        self.assertIn("limite", generar_respuesta_nvidia("hola"))

    @mock.patch.dict(os.environ, {"NVIDIA_API_KEY": "clave-prueba"})
    @mock.patch("ia.nvidia.request.urlopen")
    def test_nvidia_timeout_json_invalido_y_vacia(self, urlopen):
        urlopen.side_effect = socket.timeout()
        self.assertIn("demasiado", generar_respuesta_nvidia("hola"))

        urlopen.side_effect = None
        urlopen.return_value = RespuestaHTTPFalsa(b"no-json")
        self.assertIn("JSON", generar_respuesta_nvidia("hola"))

        urlopen.return_value = RespuestaHTTPFalsa(b'{"choices":[]}')
        self.assertIn("vacia", generar_respuesta_nvidia("hola"))

    @mock.patch("ia.proveedor.generar_respuesta_ollama")
    @mock.patch("ia.proveedor.generar_respuesta_nvidia_diagnostico")
    def test_nvidia_responde_y_ollama_no_se_llama(self, nvidia, ollama):
        nvidia.return_value = DiagnosticoNvidia(
            texto="Respuesta principal",
            endpoint=NVIDIA_URL,
            modelo="modelo",
            api_detectada=True,
            http=200,
            mensaje="OK",
            tiempo=0.1,
            timeout=25,
        )

        respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertEqual(respuesta.proveedor, "nvidia")
        self.assertFalse(respuesta.error)
        ollama.assert_not_called()

    @mock.patch("ia.proveedor.generar_respuesta_ollama")
    @mock.patch("ia.proveedor.generar_respuesta_nvidia_diagnostico")
    def test_nvidia_falla_y_ollama_responde(self, nvidia, ollama):
        nvidia.return_value = DiagnosticoNvidia(
            texto="No pude usar NVIDIA Cloud: sin red.",
            endpoint=NVIDIA_URL,
            modelo="modelo",
            api_detectada=True,
            http=None,
            mensaje="sin red",
            tiempo=0.1,
            timeout=25,
        )
        ollama.return_value = "Respuesta local"

        respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertEqual(respuesta.proveedor, "ollama")
        self.assertEqual(respuesta.texto, "Respuesta local")

    @mock.patch("ia.proveedor.generar_respuesta_ollama")
    @mock.patch("ia.proveedor.generar_respuesta_nvidia_diagnostico")
    def test_ambos_fallan_controlado(self, nvidia, ollama):
        nvidia.return_value = DiagnosticoNvidia(
            texto="No pude usar NVIDIA Cloud: sin red.",
            endpoint=NVIDIA_URL,
            modelo="modelo",
            api_detectada=True,
            http=None,
            mensaje="sin red",
            tiempo=0.1,
            timeout=25,
        )
        ollama.return_value = "No pude usar Ollama: sin servicio."

        respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertTrue(respuesta.error)
        self.assertEqual(respuesta.proveedor, "ninguno")

    @mock.patch("ia.proveedor.generar_respuesta_ollama")
    @mock.patch("ia.proveedor.generar_respuesta_nvidia_diagnostico")
    def test_proveedor_ollama_usa_ollama_directo(self, nvidia, ollama):
        self.config["ia"]["proveedor"] = "ollama"
        ollama.return_value = "Respuesta local"

        respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertEqual(respuesta.proveedor, "ollama")
        nvidia.assert_not_called()

    @mock.patch("core.cerebro.generar_respuesta")
    def test_que_version_tiene_python_llega_a_ia(self, proveedor):
        from ia.proveedor import RespuestaProveedor

        proveedor.return_value = RespuestaProveedor("Usa python --version", "nvidia")

        resultado = procesar("que version tiene python", self.memoria, self.config)

        self.assertEqual(detectar_intencion("que version tiene python"), "desconocido")
        self.assertEqual(resultado.accion, "respuesta_ia_nvidia")
        proveedor.assert_called_once()

    def test_version_memoria_sigue_funcionando(self):
        self.assertEqual(VERSION_MEMORIA, 6)
        memoria = inicializar_memoria({"sistema": {"version_memoria": 5}})
        self.assertEqual(memoria["sistema"]["version_memoria"], VERSION_MEMORIA)


if __name__ == "__main__":
    unittest.main()
