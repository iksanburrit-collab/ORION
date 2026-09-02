import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from utilidades.archivos import guardar_json
from utilidades.rutas import configurar_base_datos, raiz_proyecto, ruta_memoria


class RutasDatosTests(unittest.TestCase):
    def tearDown(self):
        configurar_base_datos(None)

    def test_orion_data_dir_tiene_prioridad(self):
        with tempfile.TemporaryDirectory() as temporal, mock.patch.dict(
            os.environ, {"ORION_DATA_DIR": temporal}
        ):
            self.assertEqual(raiz_proyecto(), Path(temporal).resolve())

    def test_base_de_pruebas_tiene_prioridad_sobre_el_entorno(self):
        with (
            tempfile.TemporaryDirectory() as temporal,
            tempfile.TemporaryDirectory() as pruebas,
            mock.patch.dict(os.environ, {"ORION_DATA_DIR": temporal}),
        ):
            configurar_base_datos(pruebas)
            self.assertEqual(raiz_proyecto(), Path(pruebas).resolve())

    def test_ruta_por_defecto_usa_el_directorio_de_la_plataforma(self):
        with tempfile.TemporaryDirectory() as temporal:
            codigo = Path(temporal, "codigo")
            codigo.mkdir()
            datos = Path(temporal, "datos")
            with mock.patch(
                "utilidades.rutas._RAIZ_PROYECTO", codigo
            ), mock.patch.dict(os.environ, {}, clear=True), mock.patch(
                "utilidades.rutas.platform.system", return_value="Linux"
            ), mock.patch(
                "utilidades.rutas.user_data_dir", return_value=str(datos)
            ) as directorio:
                self.assertEqual(raiz_proyecto(), datos)
                directorio.assert_called_once_with("orion", appauthor=False)

    def test_crea_el_directorio_de_datos_al_guardar(self):
        with tempfile.TemporaryDirectory() as temporal, mock.patch.dict(
            os.environ, {"ORION_DATA_DIR": str(Path(temporal, "datos"))}
        ):
            ruta = Path(ruta_memoria())
            self.assertFalse(ruta.parent.exists())
            guardar_json(ruta, {"estado": "listo"})
            self.assertTrue(ruta.parent.is_dir())
            self.assertTrue(ruta.is_file())

    def test_datos_legacy_en_la_raiz_siguen_usandose(self):
        with tempfile.TemporaryDirectory() as temporal:
            codigo = Path(temporal, "codigo")
            codigo.mkdir()
            (codigo / "memoria.json").write_text("{}")
            with mock.patch(
                "utilidades.rutas._RAIZ_PROYECTO", codigo
            ), mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(raiz_proyecto(), codigo)

    def test_orion_data_dir_tiene_prioridad_sobre_archivos_legacy(self):
        with tempfile.TemporaryDirectory() as temporal:
            codigo = Path(temporal, "codigo")
            codigo.mkdir()
            (codigo / "memoria.json").write_text("{}")
            datos = Path(temporal, "datos")
            with mock.patch(
                "utilidades.rutas._RAIZ_PROYECTO", codigo
            ), mock.patch.dict(os.environ, {"ORION_DATA_DIR": str(datos)}):
                self.assertEqual(raiz_proyecto(), datos)


if __name__ == "__main__":
    unittest.main()