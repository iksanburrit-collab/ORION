import os
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.conocimiento import clasificar_gusto, normalizar_para_busqueda
from core.memoria import aprender, guardar_memoria, inicializar_memoria
from utilidades.archivos import cargar
from utilidades.rutas import configurar_base_datos


class ClasificacionGustosTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"modo": "normal"}

    def tearDown(self):
        configurar_base_datos(None)
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    def procesar(self, texto):
        return procesar(texto, self.memoria, self.config)

    def test_clasifica_videojuegos_por_reglas_y_entidades(self):
        self.assertEqual(
            clasificar_gusto(
                "arena breakout",
                "me gusta arena breakout",
            ).categoria,
            "videojuegos",
        )
        self.assertEqual(
            clasificar_gusto("factorio", "me gusta factorio").categoria,
            "videojuegos",
        )
        self.assertEqual(
            clasificar_gusto(
                "satisfactory",
                "me gusta satisfactory",
            ).categoria,
            "videojuegos",
        )

    def test_clasifica_comida_musica_y_deportes(self):
        self.assertEqual(
            clasificar_gusto("pasta", "me gusta la pasta").categoria,
            "comida",
        )
        self.assertEqual(
            clasificar_gusto("rock", "me gusta el rock").categoria,
            "musica",
        )
        self.assertEqual(
            clasificar_gusto("voleibol", "me gusta voleibol").categoria,
            "deportes",
        )

    def test_clasifica_aprendizaje_y_herramientas_por_contexto(self):
        aprendizaje = aprender(
            "estoy aprendiendo python",
            self.memoria,
            guardar=False,
        )
        herramienta = aprender("uso git", self.memoria, guardar=False)

        self.assertEqual(aprendizaje.tipo, "aprendizaje")
        self.assertEqual(aprendizaje.categoria, "lenguajes")
        self.assertIn("Python", self.memoria["aprendizaje"]["lenguajes"])
        self.assertEqual(herramienta.tipo, "herramienta")
        self.assertIn("Git", self.memoria["usuario"]["herramientas"]["tecnologia"])

    def test_valor_desconocido_va_a_otros_con_baja_confianza(self):
        clasificacion = clasificar_gusto(
            "flarbnar",
            "me gusta flarbnar",
        )

        self.assertEqual(clasificacion.categoria, "otros")
        self.assertLess(clasificacion.confianza, 0.6)

    def test_evitar_duplicados_y_persistencia(self):
        self.procesar("me gusta arena breakout")
        self.procesar("me gusta Arena Breakout")
        guardar_memoria(self.memoria, "memoria_prueba.json")

        recargada = inicializar_memoria(cargar("memoria_prueba.json", {}))

        self.assertEqual(
            recargada["usuario"]["gustos"]["videojuegos"],
            ["Arena Breakout"],
        )

    def test_consultas_por_categoria_y_listado_completo(self):
        self.procesar("me gusta arena breakout")
        self.procesar("me gusta la musica")
        self.procesar("me gusta la pasta")
        self.procesar("me gusta voleibol")

        videojuegos = self.procesar("que videojuegos me gustan").respuesta
        musica = self.procesar("que musica me gusta").respuesta
        comida = self.procesar("que comidas me gustan").respuesta
        deportes = self.procesar("que deportes me gustan").respuesta
        completo = self.procesar("que me gusta").respuesta

        self.assertIn("Arena Breakout", videojuegos)
        self.assertIn("musica", normalizar_para_busqueda(musica))
        self.assertIn("pasta", comida)
        self.assertIn("voleibol", deportes)
        self.assertIn("videojuegos:", completo)
        self.assertIn("musica:", completo)
        self.assertIn("comida:", completo)
        self.assertIn("deportes:", completo)


if __name__ == "__main__":
    unittest.main()
