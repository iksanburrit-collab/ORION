import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from servicios.sistema.acciones_pc import abrir_aplicacion, cerrar_aplicacion
from servicios.sistema.aplicaciones import CatalogoAplicaciones


class AplicacionesSegurasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.exe = os.path.join(self.tmp.name, "app.exe")
        Path(self.exe).write_text("", encoding="utf-8")
        self.catalogo = CatalogoAplicaciones(os.path.join(self.tmp.name, "apps.json"))
        self.catalogo.agregar_manual("App Prueba", self.exe, ["app"])
        self.config = {
            "ia": {"activada": False},
            "sistema": {
                "control_pc_activado": True,
                "confirmar_riesgo_medio": True,
                "permitir_riesgo_alto": False,
            },
        }

    def tearDown(self):
        self.tmp.cleanup()

    @mock.patch("servicios.sistema.acciones_pc.subprocess.Popen")
    def test_abrir_aplicacion_permitida_sin_shell(self, popen):
        resultado = abrir_aplicacion("app", self.catalogo)

        self.assertTrue(resultado.exito)
        popen.assert_called_once_with([self.exe], shell=False)

    def test_rechazar_aplicacion_no_permitida(self):
        resultado = abrir_aplicacion("desconocida", self.catalogo)

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "aplicacion_no_registrada")

    def test_pedir_confirmacion_para_cerrar(self):
        resultado = procesar("cierra app", {}, self.config)

        self.assertEqual(resultado.accion, "solicitar_cierre_aplicacion")
        self.assertIsInstance(resultado.solicitud_pendiente, dict)
        self.assertEqual(resultado.solicitud_pendiente["identificador"], "app")
        self.assertEqual(
            resultado.solicitud_pendiente["accion"],
            "cerrar_aplicacion",
        )
        self.assertIn("aplicacion", resultado.solicitud_pendiente["datos"])

    def test_no_cerrar_proceso_critico(self):
        catalogo = CatalogoAplicaciones(os.path.join(self.tmp.name, "criticos.json"))
        explorer = os.path.join(self.tmp.name, "explorer.exe")
        Path(explorer).write_text("", encoding="utf-8")
        catalogo.agregar_manual("Explorador", explorer, ["explorer"])

        resultado = cerrar_aplicacion("explorer", catalogo, procesos=[
            {"name": "explorer.exe", "pid": "123"}
        ])

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "proceso_critico")

    def test_aliases_funcionan(self):
        self.assertEqual(self.catalogo.buscar("app").nombre, "App Prueba")

    @mock.patch("core.cerebro.generar_respuesta")
    def test_ia_no_ejecuta_acciones_directamente(self, generar):
        resultado = procesar("abre aplicacion inventada", {}, {"ia": {"activada": True}})

        self.assertNotEqual(resultado.accion, "respuesta_ia_groq")
        generar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
