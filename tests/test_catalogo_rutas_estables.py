import os
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.handlers.aplicaciones import procesar_aplicaciones
from servicios.calendario.local import ProveedorCalendarioLocal
from servicios.sistema.aplicaciones import CatalogoAplicaciones
from servicios.sistema.contratos import AplicacionRegistrada
from utilidades.rutas import (
    configurar_base_datos,
    ruta_aplicaciones_usuario,
    ruta_calendario_local,
    ruta_configuracion,
    ruta_memoria,
    ruta_notas,
    ruta_recordatorios,
)


class CatalogoRutasEstablesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def _app(self, indice, nombre=None):
        return AplicacionRegistrada(
            nombre=nombre or f"Aplicacion {indice}",
            aliases=[f"app{indice}"],
            ruta=os.path.join(self.tmp.name, f"app-{indice}.exe"),
            origen="menu_inicio",
            verificada=True,
            ultima_deteccion="2026-07-15T00:00:00+00:00",
        )

    def test_147_identidades_no_se_reducen_por_nombres_parciales(self):
        catalogo = CatalogoAplicaciones()
        detectadas = [self._app(indice) for indice in range(147)]

        primero = catalogo.actualizar_desde_descubrimiento(detectadas)
        segundo = CatalogoAplicaciones().actualizar_desde_descubrimiento(detectadas)

        self.assertEqual(primero["nuevas"], 147)
        self.assertEqual(len(CatalogoAplicaciones().listar()), 147)
        self.assertEqual(segundo["nuevas"], 0)
        self.assertEqual(segundo["sin_cambios"], 147)

    def test_visual_studio_y_code_permanecen_separados(self):
        catalogo = CatalogoAplicaciones()
        catalogo.actualizar_desde_descubrimiento([
            self._app(1, "Visual Studio"),
            self._app(2, "Visual Studio Code"),
        ])

        nombres = [app.nombre for app in catalogo.listar()]
        self.assertEqual(nombres, ["Visual Studio", "Visual Studio Code"])
        self.assertEqual(
            catalogo.buscar_para_usuario("studio code").nombre,
            "Visual Studio Code",
        )
        self.assertIsNotNone(catalogo.buscar_para_usuario("visual"))

    def test_identidad_sin_ruta_usa_nombre_origen_y_tipo(self):
        catalogo = CatalogoAplicaciones()
        primera = AplicacionRegistrada("Editor", ["editor"], "", origen="web")
        segunda = AplicacionRegistrada("Editor Pro", ["editorpro"], "", origen="web")

        resumen = catalogo.actualizar_desde_descubrimiento([primera, segunda])

        self.assertEqual(resumen["nuevas"], 2)
        self.assertEqual(len(CatalogoAplicaciones().listar()), 2)

    def test_listado_recarga_el_mismo_catalogo_persistido(self):
        CatalogoAplicaciones().actualizar_desde_descubrimiento([self._app(1, "Chrome")])

        procesado = procesar_aplicaciones(
            "lista aplicaciones",
            {"ia": {"activada": False}},
            catalogo=CatalogoAplicaciones(),
        )

        self.assertIn("Aplicaciones registradas: 1", procesado[2])
        self.assertIn("Chrome", procesado[2])

    def test_listado_limita_a_20_e_indica_restantes(self):
        catalogo = CatalogoAplicaciones()
        catalogo.actualizar_desde_descubrimiento([
            self._app(indice) for indice in range(25)
        ])

        respuesta = procesar_aplicaciones(
            "lista aplicaciones",
            {"ia": {"activada": False}},
            catalogo=CatalogoAplicaciones(),
        )[2]

        self.assertIn("Aplicaciones registradas: 25", respuesta)
        self.assertIn("... y 5 mas.", respuesta)
        self.assertEqual(sum(linea.startswith("- ") for linea in respuesta.splitlines()), 20)

    def test_componentes_ignoran_un_cwd_distinto(self):
        otro_cwd = tempfile.TemporaryDirectory()
        original = os.getcwd()
        try:
            os.chdir(otro_cwd.name)
            catalogo = CatalogoAplicaciones()
            calendario = ProveedorCalendarioLocal()

            self.assertEqual(catalogo.archivo, ruta_aplicaciones_usuario())
            self.assertEqual(calendario.archivo, ruta_calendario_local())
            for ruta in (
                ruta_memoria(),
                ruta_notas(),
                ruta_recordatorios(),
                ruta_configuracion(),
            ):
                self.assertTrue(Path(ruta).is_relative_to(Path(self.tmp.name)))
        finally:
            os.chdir(original)
            otro_cwd.cleanup()


if __name__ == "__main__":
    unittest.main()
