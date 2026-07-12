import os
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.memoria import (
    CONFIANZA_INFERENCIA,
    CONFIANZA_USUARIO,
    aprender,
    construir_contexto_para_ia,
    guardar_memoria,
    inicializar_memoria,
    registrar_episodio,
    seleccionar_recuerdos_relevantes,
)
from utilidades.archivos import cargar


class MemoriaEpisodicaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.memoria = inicializar_memoria({})

    def tearDown(self):
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    def test_registrar_episodio(self):
        registrado = registrar_episodio(
            self.memoria,
            "gusto",
            "Minecraft",
            categoria="videojuegos",
            fuente="usuario",
            confianza=CONFIANZA_USUARIO,
        )

        self.assertTrue(registrado)
        self.assertEqual(len(self.memoria["episodica"]["eventos"]), 1)
        self.assertEqual(
            self.memoria["episodica"]["eventos"][0]["tipo"],
            "gusto",
        )

    def test_no_duplicar_episodios_iguales(self):
        registrar_episodio(
            self.memoria,
            "gusto",
            "Minecraft",
            categoria="videojuegos",
        )
        duplicado = registrar_episodio(
            self.memoria,
            "gusto",
            "minecraft",
            categoria="videojuegos",
        )

        self.assertFalse(duplicado)
        self.assertEqual(len(self.memoria["episodica"]["eventos"]), 1)

    def test_guardar_fuente_y_confianza(self):
        aprender(
            "me gusta minecraft",
            self.memoria,
            guardar=False,
            fuente="usuario",
            confianza=CONFIANZA_USUARIO,
        )
        registrar_episodio(
            self.memoria,
            "gusto",
            "automatizacion",
            categoria="tecnologia",
            fuente="inferencia",
            confianza=CONFIANZA_INFERENCIA,
        )

        fuentes = {
            evento["contenido"]: evento["fuente"]
            for evento in self.memoria["episodica"]["eventos"]
        }
        confianzas = {
            evento["contenido"]: evento["confianza"]
            for evento in self.memoria["episodica"]["eventos"]
        }

        self.assertEqual(fuentes["Minecraft"], "usuario")
        self.assertEqual(confianzas["Minecraft"], CONFIANZA_USUARIO)
        self.assertEqual(fuentes["automatizacion"], "inferencia")
        self.assertEqual(confianzas["automatizacion"], CONFIANZA_INFERENCIA)

    def test_seleccionar_recuerdos_relevantes(self):
        registrar_episodio(
            self.memoria,
            "gusto",
            "Minecraft",
            categoria="videojuegos",
            confianza=1.0,
        )
        registrar_episodio(
            self.memoria,
            "aprendizaje",
            "Python",
            categoria="lenguajes",
            confianza=1.0,
        )

        recuerdos = seleccionar_recuerdos_relevantes(
            self.memoria,
            consulta="que sabes de python",
            limite=1,
        )

        self.assertEqual(recuerdos[0]["contenido"], "Python")

    def test_respetar_limite_de_contexto(self):
        self.memoria["perfil"]["nombre"] = "michel"

        for indice in range(10):
            registrar_episodio(
                self.memoria,
                "gusto",
                f"Recuerdo Largo {indice}",
                categoria="otros",
            )

        contexto = construir_contexto_para_ia(
            self.memoria,
            consulta="recuerdo",
            limite=80,
        )

        self.assertLessEqual(len(contexto), 80)
        self.assertIn("Perfil", contexto)

    def test_persistencia_tras_guardar_y_cargar(self):
        registrar_episodio(
            self.memoria,
            "objetivo",
            "Terminar ORION",
            categoria="otros",
        )
        guardar_memoria(self.memoria, "memoria_prueba.json")

        recargada = inicializar_memoria(cargar("memoria_prueba.json", {}))

        self.assertEqual(
            recargada["episodica"]["eventos"][0]["contenido"],
            "Terminar ORION",
        )

    def test_compatibilidad_con_memoria_antigua(self):
        antigua = {
            "nombre": "michel",
            "fecha_nacimiento": "2009-02-09",
            "historial": [],
            "frases_importantes": ["me gusta minecraft"],
        }

        migrada = inicializar_memoria(antigua)

        self.assertIn("episodica", migrada)
        self.assertIn("eventos", migrada["episodica"])
        self.assertEqual(migrada["perfil"]["nombre"], "michel")
        self.assertIn("Minecraft", migrada["usuario"]["gustos"]["videojuegos"])


if __name__ == "__main__":
    unittest.main()
