import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import completar_solicitud, procesar
from core.memoria import inicializar_memoria
from utilidades.rutas import configurar_base_datos


class MemoriaConversacionalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {
            "ia": {"activada": False},
            "memoria_conversacional": {
                "activada": True,
                "confianza_minima": 0.58,
            },
        }

    def tearDown(self):
        configurar_base_datos(None)
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    def eventos(self):
        return self.memoria["episodica"]["eventos"]

    def test_guarda_decision_importante(self):
        resultado = procesar(
            "decidi usar groq como proveedor principal",
            self.memoria,
            self.config,
        )

        self.assertEqual(resultado.accion, "guardar_memoria_conversacional")
        self.assertEqual(len(self.eventos()), 1)
        self.assertEqual(self.eventos()[0]["tipo"], "herramienta")

    def test_no_guarda_saludo(self):
        resultado = procesar("hola", self.memoria, self.config)

        self.assertEqual(resultado.accion, "saludar")
        self.assertEqual(self.eventos(), [])

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_no_guarda_pregunta_general(self, generar):
        self.config["ia"]["activada"] = True
        generar.return_value.texto = "Respuesta"
        generar.return_value.error = False
        generar.return_value.proveedor = "groq"
        generar.return_value.diagnostico = None

        resultado = procesar("que es una base de datos?", self.memoria, self.config)

        self.assertEqual(resultado.accion, "respuesta_ia_groq")
        self.assertEqual(self.eventos(), [])

    def test_evitar_duplicados(self):
        procesar("decidi usar groq como proveedor principal", self.memoria, self.config)
        procesar("decidi usar groq como proveedor principal", self.memoria, self.config)

        self.assertEqual(len(self.eventos()), 1)

    def test_pide_confirmacion_con_confianza_media(self):
        resultado = procesar(
            "tuve un problema con el modulo de memoria",
            self.memoria,
            self.config,
        )

        self.assertEqual(resultado.accion, "solicitar_confirmacion_memoria")
        self.assertIsInstance(resultado.solicitud_pendiente, dict)
        self.assertEqual(self.eventos(), [])

    def test_negativa_no_guarda_nada(self):
        resultado = procesar(
            "tuve un problema con el modulo de memoria",
            self.memoria,
            self.config,
        )
        confirmado = completar_solicitud(
            resultado.solicitud_pendiente,
            "no",
            self.memoria,
            self.config,
        )

        self.assertEqual(confirmado.accion, "confirmacion_cancelada")
        self.assertEqual(self.eventos(), [])


if __name__ == "__main__":
    unittest.main()
