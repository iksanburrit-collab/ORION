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
from ia.contratos import RespuestaIA, SolicitudIA
from ia.groq import GROQ_URL, responder as responder_groq
from ia.proveedor import (
    config_ia_migrada_correctamente,
    generar_respuesta,
    migrar_config_ia,
    normalizar_config_ia,
)
from utilidades.archivos import guardar_json
from utilidades.configuracion import cargar_configuracion
from utilidades.rutas import configurar_base_datos


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


def respuesta_ok(proveedor: str, texto: str = "Respuesta") -> RespuestaIA:
    return RespuestaIA(
        texto=texto,
        proveedor=proveedor,
        modelo=f"modelo-{proveedor}",
        error=False,
        latencia=0.1,
    )


def respuesta_error(proveedor: str, tipo_error: str = "sin_conexion") -> RespuestaIA:
    return RespuestaIA(
        texto=f"No pude usar {proveedor}",
        proveedor=proveedor,
        modelo=f"modelo-{proveedor}",
        error=True,
        tipo_error=tipo_error,
        latencia=0.1,
    )


class ProveedorHibridoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {
            "modo": "normal",
            "ia": {
                "activada": True,
                "router": {"orden_proveedores": ["groq", "ollama"]},
                "proveedores": {
                    "groq": {
                        "activado": True,
                        "modelo": "llama-3.1-8b-instant",
                        "timeout": 15,
                        "max_tokens": 180,
                        "temperature": 0.6,
                        "top_p": 0.9,
                    },
                    "ollama": {
                        "activado": True,
                        "modelo": "qwen3:1.7b",
                        "timeout": 45,
                        "keep_alive": "10m",
                        "num_predict": 90,
                        "num_ctx": 2048,
                    },
                },
                "limite_contexto": 700,
                "max_turnos": 4,
                "debug_rendimiento": True,
            },
        }

    def tearDown(self):
        configurar_base_datos(None)
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    @mock.patch.dict(os.environ, {"GROQ_API_KEY": "clave-prueba"})
    @mock.patch("ia.groq.request.urlopen")
    def test_payload_groq_correcto_y_extrae_content(self, urlopen):
        urlopen.return_value = RespuestaHTTPFalsa(
            b'{"choices":[{"message":{"content":"Respuesta Groq"}}]}'
        )

        respuesta = responder_groq(SolicitudIA(
            mensaje="hola",
            contexto="Perfil: nombre Michel",
            modelo="modelo-configurado",
            timeout=7,
            limite_salida=123,
            opciones={"temperature": 0.2, "top_p": 0.7},
        ))
        solicitud = urlopen.call_args.args[0]
        payload = json.loads(solicitud.data.decode("utf-8"))

        self.assertFalse(respuesta.error)
        self.assertEqual(respuesta.texto, "Respuesta Groq")
        self.assertEqual(solicitud.full_url, GROQ_URL)
        self.assertEqual(payload["model"], "modelo-configurado")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["max_completion_tokens"], 123)
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["top_p"], 0.7)
        self.assertEqual(solicitud.headers["Authorization"], "Bearer clave-prueba")
        self.assertEqual(solicitud.headers["Content-type"], "application/json")
        self.assertEqual(solicitud.headers["Accept"], "application/json")
        self.assertEqual(solicitud.headers["User-agent"], "ORION/2.0 Python")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 7)
        self.assertNotIn("clave-prueba", respuesta.texto)

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_groq_api_key_ausente(self):
        respuesta = responder_groq(SolicitudIA("hola"))

        self.assertTrue(respuesta.error)
        self.assertEqual(respuesta.tipo_error, "api_key_ausente")
        self.assertNotIn("GROQ_API_KEY=", respuesta.texto)

    @mock.patch.dict(os.environ, {"GROQ_API_KEY": "clave-prueba"})
    @mock.patch("ia.groq.request.urlopen")
    def test_groq_http_401_429_y_modelo_no_disponible(self, urlopen):
        urlopen.side_effect = error.HTTPError(
            GROQ_URL,
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":{"message":"bad key"}}'),
        )
        self.assertEqual(
            responder_groq(SolicitudIA("hola")).tipo_error,
            "credenciales_invalidas",
        )

        urlopen.side_effect = error.HTTPError(
            GROQ_URL,
            429,
            "Rate limit",
            hdrs=None,
            fp=io.BytesIO(b'{"error":{"message":"rate"}}'),
        )
        self.assertEqual(responder_groq(SolicitudIA("hola")).tipo_error, "limite_uso")

        urlopen.side_effect = error.HTTPError(
            GROQ_URL,
            404,
            "Not found",
            hdrs=None,
            fp=io.BytesIO(b'{"error":{"message":"model not found"}}'),
        )
        self.assertEqual(
            responder_groq(SolicitudIA("hola")).tipo_error,
            "modelo_no_disponible",
        )

    @mock.patch.dict(os.environ, {"GROQ_API_KEY": "clave-prueba"})
    @mock.patch("ia.groq.request.urlopen")
    def test_groq_timeout_json_invalido_vacia_y_formato(self, urlopen):
        urlopen.side_effect = socket.timeout()
        self.assertEqual(responder_groq(SolicitudIA("hola")).tipo_error, "timeout")

        urlopen.side_effect = None
        urlopen.return_value = RespuestaHTTPFalsa(b"no-json")
        self.assertEqual(
            responder_groq(SolicitudIA("hola")).tipo_error,
            "json_invalido",
        )

        urlopen.return_value = RespuestaHTTPFalsa(
            b'{"choices":[{"message":{"content":""}}]}'
        )
        self.assertEqual(
            responder_groq(SolicitudIA("hola")).tipo_error,
            "respuesta_vacia",
        )

        urlopen.return_value = RespuestaHTTPFalsa(b'{"choices":[]}')
        self.assertEqual(
            responder_groq(SolicitudIA("hola")).tipo_error,
            "formato_inesperado",
        )

    @mock.patch("ia.proveedor.construir_contexto_para_ia")
    def test_groq_responde_y_ollama_no_se_llama(self, contexto):
        contexto.return_value = "contexto"
        groq = mock.Mock(return_value=respuesta_ok("groq", "Respuesta cloud"))
        ollama = mock.Mock(return_value=respuesta_ok("ollama", "Respuesta local"))

        with mock.patch.dict("ia.proveedor.PROVEEDORES", {
            "groq": groq,
            "ollama": ollama,
        }):
            respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertEqual(respuesta.proveedor, "groq")
        self.assertEqual(respuesta.texto, "Respuesta cloud")
        groq.assert_called_once()
        ollama.assert_not_called()
        contexto.assert_called_once()

    def test_groq_falla_y_ollama_responde(self):
        groq = mock.Mock(return_value=respuesta_error("groq"))
        ollama = mock.Mock(return_value=respuesta_ok("ollama", "Respuesta local"))

        with mock.patch.dict("ia.proveedor.PROVEEDORES", {
            "groq": groq,
            "ollama": ollama,
        }):
            respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertEqual(respuesta.proveedor, "ollama")
        self.assertEqual(respuesta.texto, "Respuesta local")
        self.assertTrue(respuesta.diagnostico["fallback"])

    def test_groq_y_ollama_fallan_controlado(self):
        groq = mock.Mock(return_value=respuesta_error("groq"))
        ollama = mock.Mock(return_value=respuesta_error("ollama", "timeout"))

        with mock.patch.dict("ia.proveedor.PROVEEDORES", {
            "groq": groq,
            "ollama": ollama,
        }):
            respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertTrue(respuesta.error)
        self.assertEqual(respuesta.proveedor, "ninguno")
        self.assertEqual(respuesta.tipo_error, "todos_fallaron")

    def test_proveedores_desactivados_se_omiten(self):
        self.config["ia"]["proveedores"]["groq"]["activado"] = False
        self.config["ia"]["proveedores"]["ollama"]["activado"] = False
        groq = mock.Mock(return_value=respuesta_ok("groq"))
        ollama = mock.Mock(return_value=respuesta_ok("ollama"))

        with mock.patch.dict("ia.proveedor.PROVEEDORES", {
            "groq": groq,
            "ollama": ollama,
        }):
            respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertTrue(respuesta.error)
        groq.assert_not_called()
        ollama.assert_not_called()

    def test_orden_se_respeta_y_no_repite(self):
        self.config["ia"]["router"]["orden_proveedores"] = ["ollama", "groq", "ollama"]
        llamadas = []

        def groq(solicitud):
            llamadas.append("groq")
            return respuesta_ok("groq")

        def ollama(solicitud):
            llamadas.append("ollama")
            return respuesta_error("ollama")

        with mock.patch.dict("ia.proveedor.PROVEEDORES", {
            "groq": groq,
            "ollama": ollama,
        }):
            respuesta = generar_respuesta("hola", self.memoria, self.config)

        self.assertEqual(respuesta.proveedor, "groq")
        self.assertEqual(llamadas, ["ollama", "groq"])

    def test_configuracion_antigua_migra_sin_sobrescribir_personalizada(self):
        config = {
            "modo": "normal",
            "ia": {
                "activada": True,
                "proveedor": "ollama",
                "fallback_local": True,
                "modelo": "modelo-local",
                "timeout": 33,
                "keep_alive": "5m",
                "num_predict": 88,
                "num_ctx": 1024,
                "limite_contexto": 650,
                "max_turnos_conversacion": 3,
            },
        }

        cambio = migrar_config_ia(config)

        self.assertTrue(cambio)
        self.assertEqual(config["modo"], "normal")
        self.assertNotIn("proveedor", config["ia"])
        self.assertNotIn("fallback_local", config["ia"])
        self.assertEqual(
            config["ia"]["router"]["orden_proveedores"],
            ["ollama"],
        )
        self.assertEqual(
            config["ia"]["proveedores"]["ollama"]["modelo"],
            "modelo-local",
        )
        self.assertEqual(config["ia"]["proveedores"]["ollama"]["timeout"], 33)
        self.assertEqual(config["ia"]["max_turnos"], 3)

    def test_configuracion_retirada_desaparece_en_normalizacion(self):
        clave = "nvidia"
        config = {"ia": {clave: {"modelo": "antiguo"}}}
        normalizada = normalizar_config_ia(config)

        self.assertNotIn(clave, normalizada)
        self.assertNotIn(clave, normalizada["proveedores"])

    def test_configuracion_antigua_en_disco_migra_y_se_guarda_limpia(self):
        vieja = {
            "modo": "ironman",
            "personalidad": {"tono": "chill"},
            "ia": {
                "activada": True,
                "modelo": "qwen3:1.7b",
                "timeout": 60,
                "limite_contexto": 1200,
                "max_turnos_conversacion": 6,
                "keep_alive": "10m",
                "proveedor": "nvidia",
                "fallback_local": True,
                "nvidia": {
                    "modelo": "modelo-retirado",
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
                "debug_rendimiento": False,
            },
        }
        defecto = {
            "modo": "normal",
            "ia": normalizar_config_ia({}),
        }
        guardar_json("config.json", vieja)

        config = cargar_configuracion("config.json", defecto)

        self.assertEqual(config["modo"], "ironman")
        self.assertEqual(config["personalidad"], {"tono": "chill"})
        self.assertTrue(config_ia_migrada_correctamente(config))
        self.assertNotIn("proveedor", config["ia"])
        self.assertNotIn("fallback_local", config["ia"])
        self.assertNotIn("nvidia", config["ia"])
        self.assertNotIn("nvidia", config["ia"]["proveedores"])
        self.assertIn("groq", config["ia"]["proveedores"])
        self.assertEqual(
            config["ia"]["proveedores"]["ollama"]["timeout"],
            60,
        )
        self.assertEqual(config["ia"]["max_turnos"], 6)

        with open("config.json", "r", encoding="utf-8") as archivo:
            guardada = json.load(archivo)

        self.assertEqual(guardada, config)
        self.assertNotIn("nvidia", json.dumps(guardada).lower())

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_que_version_tiene_python_llega_a_ia(self, proveedor):
        proveedor.return_value = RespuestaIA("Usa python --version", "groq")

        resultado = procesar("que version tiene python", self.memoria, self.config)

        self.assertEqual(detectar_intencion("que version tiene python"), "desconocido")
        self.assertEqual(resultado.accion, "respuesta_ia_groq")
        proveedor.assert_called_once()

    def test_version_memoria_sigue_funcionando(self):
        self.assertEqual(VERSION_MEMORIA, 6)
        memoria = inicializar_memoria({"sistema": {"version_memoria": 5}})
        self.assertEqual(memoria["sistema"]["version_memoria"], VERSION_MEMORIA)


if __name__ == "__main__":
    unittest.main()
