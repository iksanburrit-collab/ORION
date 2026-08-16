import os
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib import error


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from ia.contratos import RespuestaIA, SolicitudIA
from ia.groq import responder as responder_groq
from ia.ollama import ERROR_OLLAMA, responder as responder_ollama
from ia.proveedor import PROVEEDORES


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


class ContratoProveedoresTests(unittest.TestCase):
    """Cada proveedor debe cumplir el mismo contrato SolicitudIA -> RespuestaIA."""

    def test_todos_los_proveedores_son_adaptadores_registrados(self):
        self.assertIn("groq", PROVEEDORES)
        self.assertIn("ollama", PROVEEDORES)

        for nombre, adaptador in PROVEEDORES.items():
            with self.subTest(proveedor=nombre):
                self.assertTrue(callable(adaptador))

    @mock.patch.dict(os.environ, {"GROQ_API_KEY": "clave-prueba"}, clear=True)
    @mock.patch("ia.groq.request.urlopen")
    def test_groq_responde_exitosamente(self, urlopen):
        urlopen.return_value = RespuestaHTTPFalsa(
            b'{"choices":[{"message":{"content":"Hola"}}]}'
        )

        respuesta = responder_groq(SolicitudIA("hola"))

        self.assertIsInstance(respuesta, RespuestaIA)
        self.assertFalse(respuesta.error)
        self.assertEqual(respuesta.texto, "Hola")
        self.assertEqual(respuesta.proveedor, "groq")

    @mock.patch("ia.ollama.request.urlopen")
    def test_ollama_responde_exitosamente(self, urlopen):
        urlopen.return_value = RespuestaHTTPFalsa(
            b'{"message":{"content":"Hola"}}'
        )

        respuesta = responder_ollama(SolicitudIA("hola"))

        self.assertIsInstance(respuesta, RespuestaIA)
        self.assertFalse(respuesta.error)
        self.assertEqual(respuesta.texto, "Hola")
        self.assertEqual(respuesta.proveedor, "ollama")

    @mock.patch.dict(os.environ, {"GROQ_API_KEY": "clave-prueba"}, clear=True)
    @mock.patch("ia.groq.request.urlopen")
    def test_groq_falla_sin_conexion(self, urlopen):
        urlopen.side_effect = error.URLError("connection refused")

        respuesta = responder_groq(SolicitudIA("hola"))

        self.assertIsInstance(respuesta, RespuestaIA)
        self.assertTrue(respuesta.error)
        self.assertEqual(respuesta.tipo_error, "sin_conexion")
        self.assertEqual(respuesta.proveedor, "groq")

    @mock.patch("ia.ollama.request.urlopen")
    def test_ollama_falla_sin_conexion(self, urlopen):
        urlopen.side_effect = error.URLError("connection refused")

        respuesta = responder_ollama(SolicitudIA("hola"))

        self.assertIsInstance(respuesta, RespuestaIA)
        self.assertTrue(respuesta.error)
        self.assertEqual(respuesta.tipo_error, "sin_conexion")
        self.assertEqual(respuesta.proveedor, "ollama")
        self.assertTrue(respuesta.texto.startswith(ERROR_OLLAMA))

    def test_respuesta_de_error_tiene_campos_de_contrato(self):
        respuesta = RespuestaIA("", "groq", error=True, tipo_error="sin_conexion")

        self.assertEqual(respuesta.proveedor, "groq")
        self.assertTrue(respuesta.error)
        self.assertEqual(respuesta.tipo_error, "sin_conexion")


if __name__ == "__main__":
    unittest.main()