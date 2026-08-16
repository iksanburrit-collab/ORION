import unittest

from core.intenciones import detectar_intencion


class IntencionesTests(unittest.TestCase):
    def test_detecta_solo_expresiones_matematicas_validas(self):
        for texto in ("2 + 2", "raiz 9", "pot 2 3", "sqrt(16)"):
            with self.subTest(texto=texto):
                self.assertEqual(detectar_intencion(texto), "calc")

    def test_no_confunde_texto_normal_con_calculadora(self):
        for texto in ("cuentame sobre c++", "este texto - tiene guion", "calcula el promedio"):
            with self.subTest(texto=texto):
                self.assertEqual(detectar_intencion(texto), "desconocido")


if __name__ == "__main__":
    unittest.main()
