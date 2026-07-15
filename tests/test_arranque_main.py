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
from utilidades.rutas import configurar_base_datos


class ArranqueMainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def test_inicializacion_define_recordatorios_como_lista(self):
        estado = main.inicializar_orion()

        self.assertIn("recordatorios", estado)
        self.assertIsInstance(estado["recordatorios"], list)

    def test_ejecutar_llega_al_prompt_y_sale_sin_bucle_infinito(self):
        salida = io.StringIO()
        with mock.patch.object(sys, "stdout", salida), mock.patch.object(
            builtins,
            "input",
            return_value="salir",
        ) as entrada:
            main.ejecutar()

        entrada.assert_called_once_with("\nORION> ")
        self.assertIn("Iniciando ORION v2.0", salida.getvalue())
        self.assertIn("Apagando ORION", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
