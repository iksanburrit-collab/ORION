import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from servicios.sistema.acciones_pc import (
    abrir_aplicacion,
    cerrar_aplicacion,
    lanzar_en_segundo_plano,
)
from servicios.sistema.aplicaciones import CatalogoAplicaciones
from servicios.sistema.ejecutor import EjecutorAccionesPC


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
        popen.assert_called_once()
        args, kwargs = popen.call_args
        self.assertEqual(args[0], [self.exe])
        self.assertFalse(kwargs["shell"])
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
        if sys.platform != "win32":
            self.assertTrue(kwargs["start_new_session"])
        else:
            self.assertIn("creationflags", kwargs)

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

    def test_pedir_confirmacion_para_cerrar_en_linux(self):
        with mock.patch("servicios.sistema.ejecutor.platform.system", return_value="Linux"):
            resultado = procesar("cierra app", {}, self.config)

        self.assertEqual(resultado.accion, "solicitar_cierre_aplicacion")
        self.assertIsInstance(resultado.solicitud_pendiente, dict)
        self.assertEqual(resultado.solicitud_pendiente["accion"], "cerrar_aplicacion")

    def test_pedir_confirmacion_para_cerrar_en_windows(self):
        with mock.patch("servicios.sistema.ejecutor.platform.system", return_value="Windows"):
            resultado = procesar("cierra app", {}, self.config)

        self.assertEqual(resultado.accion, "solicitar_cierre_aplicacion")
        self.assertIsInstance(resultado.solicitud_pendiente, dict)
        self.assertEqual(resultado.solicitud_pendiente["accion"], "cerrar_aplicacion")

    def test_so_no_compatible_rechaza_sin_confirmacion(self):
        with mock.patch("servicios.sistema.ejecutor.platform.system", return_value="FreeBSD"):
            resultado = procesar("cierra app", {}, self.config)

        self.assertEqual(resultado.accion, "cerrar_aplicacion")
        self.assertIsNone(resultado.solicitud_pendiente)
        self.assertEqual(resultado.respuesta, "Sistema no compatible.")

    def test_so_no_compatible_marca_error_claro_en_preparar(self):
        ejecutor = EjecutorAccionesPC(self.config)
        with mock.patch("servicios.sistema.ejecutor.platform.system", return_value="FreeBSD"):
            resultado, solicitud = ejecutor.preparar(
                "cerrar_aplicacion", {"aplicacion": "app"}
            )

        self.assertIsNone(solicitud)
        self.assertIsNotNone(resultado)
        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "sistema_no_compatible")

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

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_ia_no_ejecuta_acciones_directamente(self, generar):
        resultado = procesar("abre aplicacion inventada", {}, {"ia": {"activada": True}})

        self.assertNotEqual(resultado.accion, "respuesta_ia_groq")
        generar.assert_not_called()


class LanzamientoSegundoPlanoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_lanzamiento_no_bloquea_y_el_proceso_queda_vivo(self):
        inicio = time.time()
        proceso = lanzar_en_segundo_plano(
            [sys.executable, "-c", "import time; time.sleep(5)"]
        )
        transcurrido = time.time() - inicio

        self.assertLess(transcurrido, 1.0)
        self.assertIsNone(proceso.poll())
        if sys.platform != "win32":
            self.assertNotEqual(os.getsid(proceso.pid), os.getsid(0))
        proceso.terminate()
        proceso.wait(timeout=5)

    def test_salida_de_la_aplicacion_no_contamina_la_consola(self):
        script = (
            "import sys; "
            "print('RUIDO_STDOUT'); "
            "sys.stderr.write('RUIDO_STDERR'); "
            "sys.stdout.flush(); sys.stderr.flush()"
        )
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            proceso = lanzar_en_segundo_plano([sys.executable, "-c", script])
            proceso.wait(timeout=10)

        salida = buffer.getvalue()
        self.assertNotIn("RUIDO_STDOUT", salida)
        self.assertNotIn("RUIDO_STDERR", salida)

    @unittest.skipIf(sys.platform == "win32", "Se prueba el lanzador POSIX.")
    def test_fallo_real_al_iniciar_se_informa_como_error(self):
        ruta = os.path.join(self.tmp.name, "noejecutable.exe")
        Path(ruta).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(ruta, 0o644)

        catalogo = CatalogoAplicaciones(os.path.join(self.tmp.name, "err.json"))
        catalogo.agregar_manual("No Ejecutable", ruta, ["noejecutable"])

        resultado = abrir_aplicacion("noejecutable", catalogo)

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "error_sistema")


if __name__ == "__main__":
    unittest.main()
