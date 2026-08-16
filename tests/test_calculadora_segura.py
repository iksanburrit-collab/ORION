import unittest

from comandos.calculadora import ejecutar_calculadora


class CalculadoraSeguraTests(unittest.TestCase):
    def assert_invalida(self, comando: str) -> None:
        self.assertEqual(ejecutar_calculadora(comando), "Operación inválida 😅")

    def test_operaciones_normales(self):
        self.assertEqual(ejecutar_calculadora("2 + 3 * 4"), "🧮 14")

    def test_precedencia(self):
        self.assertEqual(ejecutar_calculadora("2 + 3 * 4"), "🧮 14")

    def test_parentesis(self):
        self.assertEqual(ejecutar_calculadora("(2 + 3) * 4"), "🧮 20")

    def test_potencias_y_sintaxis_heredada(self):
        self.assertEqual(ejecutar_calculadora("2 ^ 3"), "🧮 8")
        self.assertEqual(ejecutar_calculadora("pot 2 3"), "🧮 8")

    def test_funcion_matematica_permitida_y_sintaxis_heredada(self):
        self.assertEqual(ejecutar_calculadora("sqrt(16)"), "🧮 4.0")
        self.assertEqual(ejecutar_calculadora("raiz 9"), "🧮 3.0")

    def test_rechaza_intento_de_ejecucion_de_codigo(self):
        self.assert_invalida("__import__('os').system('echo vulnerable')")
        self.assert_invalida("(lambda: 1)()")

    def test_rechaza_acceso_a_archivos(self):
        self.assert_invalida("open('secreto.txt')")

    def test_rechaza_imports(self):
        self.assert_invalida("__import__('os')")

    def test_rechaza_atributos(self):
        self.assert_invalida("(1).__class__")
        self.assert_invalida("sqrt.__call__(4)")

    def test_rechaza_expresiones_malformadas_y_nodos_no_permitidos(self):
        for comando in ("2 +", "[x for x in range(10)]", "sqrt(4, 2)", "raiz -1", "1 / 0"):
            with self.subTest(comando=comando):
                self.assert_invalida(comando)


if __name__ == "__main__":
    unittest.main()
