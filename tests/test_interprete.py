import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.interprete import (
    TIPO_APLICACION,
    TIPO_COLECCION,
    TIPO_CONSULTA,
    TIPO_OBJETO,
    TIPO_PROYECTO,
    TIPO_TAREA,
    RegistroVerbos,
    Verbo,
    analizar,
    verbos_disponibles,
)


class AnalizadorComandosSimplesTests(unittest.TestCase):
    def test_abre_steam(self):
        resultado = analizar("abre Steam")
        self.assertTrue(resultado.reconocido)
        self.assertEqual(len(resultado.operaciones), 1)

        op = resultado.operaciones[0]
        self.assertEqual(op.verbo, "abrir")
        self.assertEqual(op.entidad.valor, "Steam")
        self.assertEqual(op.entidad.tipo, TIPO_APLICACION)

    def test_cierra_chrome(self):
        op = analizar("cierra Chrome").operaciones[0]
        self.assertEqual(op.verbo, "cerrar")
        self.assertEqual(op.entidad.valor, "Chrome")
        self.assertEqual(op.entidad.tipo, TIPO_APLICACION)

    def test_termina_cierra(self):
        op = analizar("termina Steam").operaciones[0]
        self.assertEqual(op.verbo, "cerrar")
        self.assertEqual(op.entidad.valor, "Steam")

    def test_inicia_steam(self):
        op = analizar("inicia Steam").operaciones[0]
        self.assertEqual(op.verbo, "iniciar")
        self.assertEqual(op.entidad.valor, "Steam")

    def test_busca_youtube_es_consulta(self):
        op = analizar("busca YouTube").operaciones[0]
        self.assertEqual(op.verbo, "buscar")
        self.assertEqual(op.entidad.valor, "YouTube")
        self.assertEqual(op.entidad.tipo, TIPO_CONSULTA)

    def test_lista_aplicaciones(self):
        op = analizar("lista aplicaciones").operaciones[0]
        self.assertEqual(op.verbo, "listar")
        self.assertEqual(op.entidad.valor, "aplicaciones")
        self.assertEqual(op.entidad.tipo, TIPO_COLECCION)

    def test_ejecuta_las_pruebas(self):
        op = analizar("ejecuta las pruebas").operaciones[0]
        self.assertEqual(op.verbo, "ejecutar")
        self.assertEqual(op.entidad.valor, "las pruebas")
        self.assertEqual(op.entidad.tipo, TIPO_TAREA)

    def test_crea_tarea(self):
        op = analizar("crea tarea").operaciones[0]
        self.assertEqual(op.verbo, "crear")
        self.assertEqual(op.entidad.tipo, TIPO_OBJETO)

    def test_agrega_tarea(self):
        op = analizar("agrega tarea").operaciones[0]
        self.assertEqual(op.verbo, "crear")
        self.assertEqual(op.entidad.valor, "tarea")

    def test_dime_consulta(self):
        resultado = analizar("dime que juegos tengo instalados")
        self.assertTrue(resultado.reconocido)
        op = resultado.operaciones[0]
        self.assertEqual(op.verbo, "consultar")
        self.assertEqual(op.entidad.tipo, TIPO_CONSULTA)

    def test_abre_mi_proyecto_es_proyecto(self):
        op = analizar("abre mi proyecto ORION").operaciones[0]
        self.assertEqual(op.verbo, "abrir")
        self.assertEqual(op.entidad.tipo, TIPO_PROYECTO)
        self.assertEqual(op.entidad.valor, "mi proyecto ORION")

    def test_entidad_conserva_canonico_normalizado(self):
        op = analizar("abre Visual Studio Code").operaciones[0]
        self.assertEqual(op.entidad.normalizado, "visual studio code")


class AnalizadorComandosCompuestosTests(unittest.TestCase):
    def test_abre_chrome_y_busca_youtube(self):
        resultado = analizar("abre Chrome y busca YouTube")
        self.assertTrue(resultado.reconocido)
        self.assertEqual(len(resultado.operaciones), 2)

        primera, segunda = resultado.operaciones
        self.assertEqual((primera.verbo, primera.entidad.valor), ("abrir", "Chrome"))
        self.assertEqual((segunda.verbo, segunda.entidad.valor), ("buscar", "YouTube"))

    def test_abre_vscode_y_luego_abre_mi_proyecto_orion(self):
        resultado = analizar("abre VS Code y luego abre mi proyecto ORION")
        self.assertEqual(len(resultado.operaciones), 2)

        primera, segunda = resultado.operaciones
        self.assertEqual((primera.verbo, primera.entidad.valor), ("abrir", "VS Code"))
        self.assertEqual(primera.entidad.tipo, TIPO_APLICACION)

        self.assertEqual(segunda.verbo, "abrir")
        self.assertEqual(segunda.entidad.valor, "mi proyecto ORION")
        self.assertEqual(segunda.entidad.tipo, TIPO_PROYECTO)

    def test_abre_chrome_despues_busca_gatos(self):
        resultado = analizar("abre Chrome después busca gatos")
        self.assertEqual(len(resultado.operaciones), 2)

        primera, segunda = resultado.operaciones
        self.assertEqual((primera.verbo, primera.entidad.valor), ("abrir", "Chrome"))
        self.assertEqual((segunda.verbo, segunda.entidad.valor), ("buscar", "gatos"))

    def test_abre_steam_y_dime_que_juegos_tengo(self):
        resultado = analizar("abre Steam y dime qué juegos tengo instalados")
        self.assertEqual(len(resultado.operaciones), 2)

        primera, segunda = resultado.operaciones
        self.assertEqual((primera.verbo, primera.entidad.valor), ("abrir", "Steam"))
        self.assertEqual(segunda.verbo, "consultar")
        self.assertEqual(segunda.entidad.tipo, TIPO_CONSULTA)

    def test_tres_operaciones_secuenciales(self):
        resultado = analizar("abre Chrome y luego busca gatos y abre Edge")
        self.assertEqual(len(resultado.operaciones), 3)
        verbos = [op.verbo for op in resultado.operaciones]
        self.assertEqual(verbos, ["abrir", "buscar", "abrir"])

    def test_orden_de_operaciones(self):
        resultado = analizar("abre Chrome y busca gatos")
        self.assertEqual([op.orden for op in resultado.operaciones], [0, 1])

    def test_texto_de_operacion_conserva_fragmento(self):
        resultado = analizar("abre Chrome y busca gatos")
        self.assertEqual(resultado.operaciones[0].texto, "abre Chrome")
        self.assertEqual(resultado.operaciones[1].texto, "busca gatos")


class AnalizadorConectoresTests(unittest.TestCase):
    def test_conectores_de_secuencia(self):
        conectores = (
            "y luego",
            "luego",
            "después",
            "despues",
            "posteriormente",
            "y posteriormente",
            "y despues",
        )
        for conector in conectores:
            with self.subTest(conector=conector):
                resultado = analizar(f"abre Chrome {conector} busca gatos")
                self.assertEqual(len(resultado.operaciones), 2, conector)

    def test_conector_y_simple(self):
        resultado = analizar("abre Chrome y busca gatos")
        self.assertEqual(len(resultado.operaciones), 2)

    def test_coma_entre_acciones(self):
        resultado = analizar("abre Chrome, busca gatos")
        self.assertEqual(len(resultado.operaciones), 2)
        self.assertEqual(resultado.operaciones[1].entidad.valor, "gatos")


class AnalizadorFormatoTests(unittest.TestCase):
    def test_mayusculas(self):
        op = analizar("ABRE CHROME").operaciones[0]
        self.assertEqual(op.verbo, "abrir")
        self.assertEqual(op.entidad.valor, "CHROME")

    def test_acentos_en_verbos(self):
        op = analizar("búscame gatos").operaciones[0]
        self.assertEqual(op.verbo, "buscar")
        self.assertEqual(op.entidad.valor, "gatos")

    def test_espacios_extra(self):
        resultado = analizar("   abre   Chrome   y    busca   gatos   ")
        self.assertEqual(len(resultado.operaciones), 2)
        self.assertEqual(resultado.operaciones[0].entidad.valor, "Chrome")
        self.assertEqual(resultado.operaciones[1].entidad.valor, "gatos")

    def test_puntuacion_final(self):
        op = analizar("abre Chrome.").operaciones[0]
        self.assertEqual(op.entidad.valor, "Chrome")


class AnalizadorNombresVariasPalabrasTests(unittest.TestCase):
    def test_abre_visual_studio_code_una_operacion(self):
        resultado = analizar("abre Visual Studio Code")
        self.assertEqual(len(resultado.operaciones), 1)

        op = resultado.operaciones[0]
        self.assertEqual(op.verbo, "abrir")
        self.assertEqual(op.entidad.valor, "Visual Studio Code")
        self.assertEqual(op.entidad.tipo, TIPO_APLICACION)

    def test_busca_rock_y_roll_una_operacion(self):
        resultado = analizar("busca rock y roll")
        self.assertEqual(len(resultado.operaciones), 1)

        op = resultado.operaciones[0]
        self.assertEqual(op.verbo, "buscar")
        self.assertEqual(op.entidad.valor, "rock y roll")
        self.assertEqual(op.entidad.tipo, TIPO_CONSULTA)

    def test_abre_rock_y_roll_una_operacion(self):
        resultado = analizar("abre rock y roll")
        self.assertEqual(len(resultado.operaciones), 1)
        self.assertEqual(resultado.operaciones[0].entidad.valor, "rock y roll")

    def test_abre_chrome_y_youtube_no_se_divide(self):
        resultado = analizar("abre Chrome y YouTube")
        self.assertEqual(len(resultado.operaciones), 1)
        self.assertEqual(resultado.operaciones[0].entidad.valor, "Chrome y YouTube")

    def test_abre_capitan_america_una_operacion(self):
        resultado = analizar("abre Capitán América")
        self.assertEqual(len(resultado.operaciones), 1)
        self.assertEqual(resultado.operaciones[0].entidad.valor, "Capitán América")


class AnalizadorNoReconocidosTests(unittest.TestCase):
    def test_saludo(self):
        self.assertFalse(analizar("hola").reconocido)

    def test_gusto(self):
        self.assertFalse(analizar("me gusta el cafe").reconocido)

    def test_pregunta(self):
        self.assertFalse(analizar("cual es la hora").reconocido)

    def test_vacio(self):
        self.assertFalse(analizar("").reconocido)

    def test_solo_espacios(self):
        self.assertFalse(analizar("   ").reconocido)

    def test_analisis_es_booleano(self):
        self.assertTrue(bool(analizar("abre Chrome")))
        self.assertFalse(bool(analizar("hola")))

    def test_clausula_sin_verbo_inicial_se_reporta(self):
        resultado = analizar("por favor abre Chrome y busca gatos")
        self.assertEqual(len(resultado.operaciones), 1)
        self.assertEqual(resultado.operaciones[0].entidad.valor, "gatos")
        self.assertEqual(
            resultado.fragmentos_no_reconocidos,
            ("por favor abre Chrome",),
        )


class RegistroVerbosTests(unittest.TestCase):
    def test_verbos_base_requeridos(self):
        disponibles = set(verbos_disponibles())
        requeridos = {
            "abrir",
            "cerrar",
            "iniciar",
            "buscar",
            "ejecutar",
            "listar",
            "crear",
            "consultar",
        }
        self.assertEqual(requeridos, disponibles)

    def test_registro_personalizado_se_inyecta(self):
        registro = RegistroVerbos(
            (Verbo("reproducir", ("reproduce", "reproducir"), TIPO_CONSULTA),)
        )
        resultado = analizar("reproduce musica", registro_verbos=registro)
        self.assertTrue(resultado.reconocido)

        op = resultado.operaciones[0]
        self.assertEqual(op.verbo, "reproducir")
        self.assertEqual(op.entidad.valor, "musica")

    def test_verbo_fuera_del_registro_no_se_reconoce(self):
        registro = RegistroVerbos(
            (Verbo("reproducir", ("reproduce",), TIPO_CONSULTA),)
        )
        self.assertFalse(
            analizar("abre Chrome", registro_verbos=registro).reconocido
        )

    def test_nombres_y_todos_del_registro(self):
        registro = RegistroVerbos()
        self.assertIn("abrir", registro.nombres())
        self.assertEqual({v.nombre for v in registro.todos()}, set(registro.nombres()))


if __name__ == "__main__":
    unittest.main()