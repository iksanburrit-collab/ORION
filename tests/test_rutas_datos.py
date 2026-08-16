import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from utilidades.rutas import configurar_base_datos, raiz_proyecto


class RutasDatosTests(unittest.TestCase):
    def tearDown(self):
        configurar_base_datos(None)

    def test_orion_data_dir_tiene_prioridad(self):
        with tempfile.TemporaryDirectory() as temporal, mock.patch.dict(
            os.environ, {"ORION_DATA_DIR": temporal}
        ):
            self.assertEqual(raiz_proyecto(), Path(temporal).resolve())

    def test_base_de_pruebas_tiene_prioridad_sobre_el_entorno(self):
        with tempfile.TemporaryDirectory() as temporal, tempfile.TemporaryDirectory() as pruebas:
            with mock.patch.dict(os.environ, {"ORION_DATA_DIR": temporal}):
                configurar_base_datos(pruebas)
                self.assertEqual(raiz_proyecto(), Path(pruebas).resolve())


if __name__ == "__main__":
    unittest.main()
