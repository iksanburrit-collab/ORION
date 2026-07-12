import os
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.memoria import inicializar_memoria


class MemoriaFuncionalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"modo": "normal"}

    def tearDown(self):
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    def procesar(self, texto):
        return procesar(texto, self.memoria, self.config)

    def test_consulta_videojuegos_deportes_aprendizaje_objetivos(self):
        self.procesar("me gusta minecraft")
        self.procesar("me gusta futbol")
        self.procesar("estoy aprendiendo python")
        self.procesar("mi objetivo es crear orion")

        videojuegos = self.procesar("que videojuegos me gustan")
        deportes = self.procesar("que deportes me gustan")
        aprendizaje = self.procesar("que estoy aprendiendo")
        objetivos = self.procesar("cuales son mis objetivos")

        self.assertIn("Minecraft", videojuegos.respuesta)
        self.assertIn("futbol", deportes.respuesta)
        self.assertIn("Python", aprendizaje.respuesta)
        self.assertIn("Crear Orion", objetivos.respuesta)

    def test_resumen_personal_y_proyectos(self):
        self.memoria["perfil"]["nombre"] = "michel"
        self.memoria["proyectos"]["ORION"] = {"estado": "activo"}
        self.procesar("me gusta factorio")

        resumen = self.procesar("que sabes de mi")
        proyectos = self.procesar("que proyectos tengo")

        self.assertIn("michel", resumen.respuesta)
        self.assertIn("Factorio", resumen.respuesta)
        self.assertIn("ORION", proyectos.respuesta)

    def test_olvidar_gusto_y_aprendizaje(self):
        self.procesar("me gusta minecraft")
        self.procesar("estoy aprendiendo python")

        olvido_gusto = self.procesar("olvida que me gusta minecraft")
        olvido_aprendizaje = self.procesar(
            "olvida que estoy aprendiendo python"
        )

        self.assertIn("olvide", olvido_gusto.respuesta)
        self.assertIn("olvide", olvido_aprendizaje.respuesta)
        self.assertNotIn(
            "Minecraft",
            self.procesar("que videojuegos me gustan").respuesta,
        )
        self.assertNotIn(
            "Python",
            self.procesar("que estoy aprendiendo").respuesta,
        )

    def test_ya_no_me_gusta_y_cambiar_objetivo(self):
        self.procesar("me gusta roblox")
        self.procesar("mi objetivo es aprender python")

        self.procesar("ya no me gusta roblox")
        cambio = self.procesar("cambia mi objetivo a terminar orion")

        self.assertIn("Objetivo actualizado", cambio.respuesta)
        self.assertNotIn(
            "Roblox",
            self.procesar("que videojuegos me gustan").respuesta,
        )
        self.assertEqual(
            self.memoria["usuario"]["objetivos"],
            ["terminar orion"],
        )

    def test_evitar_duplicados_y_recuerdos_basura(self):
        self.memoria["usuario"]["gustos"]["videojuegos"] = [
            "Minecraft",
            "minecraft",
            "",
            "que videojuegos me gustan",
        ]
        inicializar_memoria(self.memoria)
        self.procesar("me gusta minecraft")

        self.assertEqual(
            self.memoria["usuario"]["gustos"]["videojuegos"],
            ["Minecraft"],
        )


if __name__ == "__main__":
    unittest.main()
