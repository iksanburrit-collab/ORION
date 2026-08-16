import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.skills import (
    SkillNoEncontrada,
    SkillRegistry,
    obtener_skill,
    skills_disponibles,
)
from core.skills.lector import leer_skill


class DescubrimientoSkillsTests(unittest.TestCase):
    def setUp(self):
        self.registro = SkillRegistry()

    def test_descubre_las_cuatro_skills_iniciales(self):
        nombres = {skill.name for skill in self.registro.descubrir()}
        self.assertEqual(nombres, {"aplicaciones", "navegador", "sistema", "archivos"})

    def test_lista_las_skills(self):
        self.assertEqual(
            self.registro.nombres(),
            ["aplicaciones", "archivos", "navegador", "sistema"],
        )
        for skill in self.registro.listar():
            self.assertIsInstance(skill.name, str)
            self.assertTrue(skill.description)


class RecuperacionSkillsTests(unittest.TestCase):
    def setUp(self):
        self.registro = SkillRegistry()

    def test_obtener_skill_por_nombre(self):
        skill = self.registro.obtener("aplicaciones")
        self.assertEqual(skill.name, "aplicaciones")
        self.assertTrue(skill.description)
        self.assertTrue(skill.instructions)

    def test_error_cuando_la_skill_no_existe(self):
        with self.assertRaises(SkillNoEncontrada) as contexto:
            self.registro.obtener("inexistente")
        self.assertIsInstance(contexto.exception, LookupError)
        self.assertEqual(contexto.exception.nombre, "inexistente")

    def test_lectura_correcta_de_skill_md(self):
        skill = self.registro.obtener("navegador")
        self.assertIn("## Cuándo utilizar", skill.instructions)
        self.assertIn("## Reglas", skill.instructions)
        self.assertTrue(skill.metadata["cuando_utilizar"])
        self.assertTrue(skill.metadata["reglas"])
        self.assertTrue(skill.metadata["fuente"].endswith("SKILL.md"))


class ValidacionFormatoTests(unittest.TestCase):
    def test_validacion_minima_del_formato(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)

            valida = raiz / "valida"
            valida.mkdir()
            (valida / "SKILL.md").write_text(
                "---\nnombre: valida\ndescripcion: Una skill de prueba.\n---\n\n"
                "# Valida\n\n## Reglas\n- algo\n",
                encoding="utf-8",
            )

            sin_descripcion = raiz / "sin_descripcion"
            sin_descripcion.mkdir()
            (sin_descripcion / "SKILL.md").write_text(
                "---\nnombre: sin_descripcion\n---\n\n# Sin descripcion\n",
                encoding="utf-8",
            )

            sin_archivo = raiz / "sin_archivo"
            sin_archivo.mkdir()

            registro = SkillRegistry(raiz)
            self.assertEqual(registro.nombres(), ["valida"])

    def test_leer_skill_devuelve_none_si_no_hay_skill_md(self):
        with tempfile.TemporaryDirectory() as temporal:
            directorio = Path(temporal) / "vacia"
            directorio.mkdir()
            self.assertIsNone(leer_skill(directorio))


class IntegracionOrionTests(unittest.TestCase):
    def test_consulta_de_skills_desde_el_cerebro(self):
        resultado = procesar("lista skills", {}, {"ia": {"activada": False}})
        self.assertEqual(resultado.accion, "listar_skills")
        for nombre in ("aplicaciones", "navegador", "sistema", "archivos"):
            self.assertIn(nombre, resultado.respuesta)

    def test_consulta_alternativa_de_skills(self):
        resultado = procesar("que skills tienes", {}, {"ia": {"activada": False}})
        self.assertEqual(resultado.accion, "listar_skills")

    def test_helpers_de_modulo(self):
        nombres = {skill.name for skill in skills_disponibles()}
        self.assertEqual(nombres, {"aplicaciones", "navegador", "sistema", "archivos"})
        self.assertEqual(obtener_skill("aplicaciones").name, "aplicaciones")


if __name__ == "__main__":
    unittest.main()