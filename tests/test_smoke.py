import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import main
from core.cerebro import procesar
from core.intenciones import detectar_intencion
from core.memoria import guardar_memoria, inicializar_memoria
from ia.contratos import RespuestaIA
from utilidades.archivos import cargar_json
from utilidades.rutas import configurar_base_datos, ruta_memoria


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"ia": {"activada": False}}

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def test_inicio_de_orion(self):
        estado = main.inicializar_orion()

        self.assertIn("memoria", estado)
        self.assertIn("config", estado)

        resultado = procesar("salir", estado["memoria"], estado["config"])

        self.assertTrue(resultado.salir)
        self.assertEqual(resultado.accion, "salir")

    def test_calculadora(self):
        resultado = procesar("2 + 3 * 4", self.memoria, self.config)

        self.assertEqual(resultado.intencion, "calc")
        self.assertEqual(resultado.accion, "calcular")
        self.assertEqual(resultado.respuesta, "🧮 14")

    def test_intenciones(self):
        self.assertEqual(detectar_intencion("hola"), "saludo")
        self.assertEqual(detectar_intencion("que hora es"), "hora")
        self.assertEqual(detectar_intencion("me gusta el cafe"), "desconocido")

    def test_memoria_y_persistencia(self):
        self.memoria["perfil"]["nombre"] = "Ana"
        guardar_memoria(self.memoria, ruta_memoria())

        recargada = inicializar_memoria(cargar_json(ruta_memoria(), {}).datos)

        self.assertEqual(recargada["perfil"]["nombre"], "Ana")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_navegador(self, abrir):
        resultado = procesar("busca gatos", self.memoria, self.config)

        self.assertEqual(resultado.accion, "navegador")
        abrir.assert_called_once()

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_proveedor_ia_con_mocks(self, generar):
        self.config["ia"] = {"activada": True}
        generar.return_value = RespuestaIA("Respuesta simulada", "groq")

        resultado = procesar("cuentame algo", self.memoria, self.config)

        self.assertEqual(resultado.accion, "respuesta_ia_groq")
        self.assertEqual(resultado.respuesta, "Respuesta simulada")
        generar.assert_called_once()


if __name__ == "__main__":
    unittest.main()