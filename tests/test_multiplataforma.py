import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from comandos.navegador import navegador_inteligente
from core.cerebro import procesar
from servicios.sistema.acciones_pc import abrir_aplicacion, cerrar_aplicacion
from servicios.sistema.aplicaciones import CatalogoAplicaciones, ruta_permitida
from utilidades import rutas


class CompatibilidadMultiplataformaTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()

    def tearDown(self):
        rutas.configurar_base_datos(None)
        self.temporal.cleanup()

    def _catalogo_con_app(self, nombre_archivo: str) -> tuple[CatalogoAplicaciones, str]:
        ruta = Path(self.temporal.name, nombre_archivo)
        ruta.touch()
        catalogo = CatalogoAplicaciones(
            str(Path(self.temporal.name, f"apps_{nombre_archivo}.json"))
        )
        catalogo.agregar_manual("App", str(ruta), ["app"])
        return catalogo, str(ruta)

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_navegacion_usa_el_navegador_estandar_en_las_tres_plataformas(self, abrir):
        for sistema in ("Windows", "Linux", "Darwin"):
            with self.subTest(sistema=sistema), mock.patch(
                "servicios.sistema.acciones_pc.platform.system", return_value=sistema
            ):
                self.assertTrue(navegador_inteligente("busca orion"))

        self.assertEqual(abrir.call_count, 3)

    def test_fallo_del_navegador_da_error_claro_al_orquestador(self):
        with mock.patch("core.tools.herramientas.navegador.navegador_inteligente", return_value=False):
            resultado = procesar("busca orion", {}, {"ia": {"activada": False}})

        self.assertEqual(resultado.accion, "error_navegador")
        self.assertIn("No pude abrir el navegador", resultado.respuesta)

    @mock.patch("servicios.sistema.acciones_pc.subprocess.Popen")
    def test_abre_formatos_por_plataforma(self, popen):
        casos = (
            ("Windows", "app.exe", None, None),
            ("Linux", "app.desktop", "/usr/bin/xdg-open", "/usr/bin/xdg-open"),
            ("Darwin", "App.app", None, "open"),
        )

        for sistema, archivo, lanzador, esperado in casos:
            with self.subTest(sistema=sistema):
                catalogo, ruta = self._catalogo_con_app(archivo)
                with mock.patch(
                    "servicios.sistema.acciones_pc.platform.system", return_value=sistema
                ), mock.patch(
                    "servicios.sistema.acciones_pc.shutil.which", return_value=lanzador
                ):
                    resultado = abrir_aplicacion("app", catalogo)

                self.assertTrue(resultado.exito)
                comando = [esperado, ruta] if esperado else [ruta]
                popen.assert_called()
                args, kwargs = popen.call_args
                self.assertEqual(args[0], comando)
                self.assertFalse(kwargs["shell"])
                self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
                self.assertIs(kwargs["stderr"], subprocess.DEVNULL)

    def test_linux_informa_si_no_hay_lanzador_desktop(self):
        catalogo, _ = self._catalogo_con_app("app.desktop")
        with mock.patch(
            "servicios.sistema.acciones_pc.platform.system", return_value="Linux"
        ), mock.patch("servicios.sistema.acciones_pc.shutil.which", return_value=None):
            resultado = abrir_aplicacion("app", catalogo)

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "capacidad_no_disponible")

    @mock.patch("servicios.sistema.acciones_pc.os.kill")
    def test_cierra_procesos_en_linux_y_macos(self, matar):
        catalogo, _ = self._catalogo_con_app("app.exe")
        for sistema in ("Linux", "Darwin"):
            with self.subTest(sistema=sistema), mock.patch(
                "servicios.sistema.acciones_pc.platform.system", return_value=sistema
            ):
                resultado = cerrar_aplicacion(
                    "app", catalogo, procesos=[{"name": "app.exe", "pid": "123"}]
                )
                self.assertTrue(resultado.exito)

        self.assertEqual(matar.call_count, 2)

    @mock.patch("servicios.sistema.acciones_pc.subprocess.run")
    def test_cierra_procesos_en_windows(self, ejecutar):
        ejecutar.return_value.returncode = 0
        catalogo, _ = self._catalogo_con_app("app.exe")
        with mock.patch(
            "servicios.sistema.acciones_pc.platform.system", return_value="Windows"
        ):
            resultado = cerrar_aplicacion(
                "app", catalogo, procesos=[{"name": "app.exe", "pid": "123"}]
            )

        self.assertTrue(resultado.exito)
        ejecutar.assert_called_once_with(
            ["taskkill", "/PID", "123", "/T"], shell=False, check=False
        )

    def test_rutas_de_datos_se_resuelven_por_plataforma(self):
        raiz = Path(self.temporal.name, "codigo")
        raiz.mkdir()

        for sistema, nombre in (
            ("Windows", "ORION"),
            ("Linux", "orion"),
            ("Darwin", "ORION"),
        ):
            with self.subTest(sistema=sistema), mock.patch.object(
                rutas, "_RAIZ_PROYECTO", raiz
            ), mock.patch.dict(os.environ, {}, clear=True), mock.patch(
                "utilidades.rutas.platform.system", return_value=sistema
            ), mock.patch(
                "utilidades.rutas.user_data_dir", return_value=f"/datos/{sistema}"
            ) as directorio_plataforma:
                self.assertEqual(
                    rutas.raiz_proyecto(), Path(f"/datos/{sistema}")
                )
                directorio_plataforma.assert_called_once_with(
                    nombre, appauthor=False
                )

    def test_catalogo_admite_formatos_de_las_tres_plataformas(self):
        for ruta in ("app.exe", "app.desktop", "App.app", "acceso.lnk"):
            with self.subTest(ruta=ruta):
                self.assertTrue(ruta_permitida(ruta))


if __name__ == "__main__":
    unittest.main()
