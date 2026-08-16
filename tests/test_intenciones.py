import unittest

from core.intenciones import detectar_intencion


class IntencionesTests(unittest.TestCase):
    def assert_intencion(self, texto: str, esperada: str) -> None:
        self.assertEqual(detectar_intencion(texto), esperada, texto)

    def test_detecta_solo_expresiones_matematicas_validas(self):
        for texto in ("2 + 2", "raiz 9", "pot 2 3", "sqrt(16)"):
            with self.subTest(texto=texto):
                self.assertEqual(detectar_intencion(texto), "calc")

    def test_no_confunde_texto_normal_con_calculadora(self):
        for texto in ("cuentame sobre c++", "este texto - tiene guion", "calcula el promedio"):
            with self.subTest(texto=texto):
                self.assertEqual(detectar_intencion(texto), "desconocido")

    def test_comandos_validos(self):
        casos = {
            "hola": "saludo",
            "hey": "saludo",
            "buenas": "saludo",
            "nombre": "nombre",
            "cual es tu nombre": "nombre",
            "cumple": "cumple",
            "cuando cumples": "cumple",
            "perfil": "perfil",
            "edad": "edad",
            "hora": "hora",
            "que hora es": "hora",
            "fecha": "fecha",
            "que fecha es": "fecha",
            "estado": "estado",
            "ayuda": "ayuda",
            "ayudame": "ayuda",
            "salir": "salir",
            "quiero salir": "salir",
        }
        for texto, esperada in casos.items():
            with self.subTest(texto=texto):
                self.assert_intencion(texto, esperada)

    def test_operaciones_matematicas_validas(self):
        for texto in (
            "2 + 2",
            "2+2",
            "100/5",
            "2*3*4",
            "(2+3)*4",
            "2 ^ 3",
            "2.5 * 4",
            "raiz 9",
            "pot 2 3",
            "sqrt(16)",
        ):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "calc")

    def test_frases_normales_no_activan_comandos(self):
        for texto in (
            "me gusta el cafe",
            "que pelicula recomiendas",
            "estoy bien gracias",
            "como esta el clima hoy",
            "cuentame algo de automatizacion",
            "que es una base de datos?",
            "que version tiene python",
        ):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "desconocido")

    def test_palabras_que_contienen_terminos_de_intencion(self):
        for texto in (
            "they are here",           # contiene "hey"
            "renombrado automatico",   # contiene "nombre"
            "sobrinombre",             # contiene "nombre"
            "feliz cumpleaños",        # contiene "cumple"
            "cumplimiento de normas",  # contiene "cumpl"
            "perfilado de metal",      # contiene "perfil"
            "estados unidos",          # contiene "estado"
            "ayudante de cocina",      # contiene "ayuda"
            "salida del tunel",        # contiene "salida"
        ):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "desconocido")

    def test_urls_no_activan_intenciones(self):
        for texto in (
            "https://example.com",
            "https://github.com/michel/perfil",
            "http://sitio.org/estado",
            "www.ejemplo.com",
        ):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "desconocido")

    def test_rutas_no_activan_intenciones(self):
        for texto in (
            "/home/usuario/documentos",
            "~/documentos",
            "/tmp/ayuda.txt",
            "C:/Program Files/app.exe",
            "./carpeta/archivo",
        ):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "desconocido")

    def test_numeros_no_activan_intenciones(self):
        for texto in (
            "123456",
            "3.14",
            "123-456-7890",   # teléfono
            "15/08/2026",     # fecha
            "2020-2025",      # rango
        ):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "desconocido")

    def test_conversacion_casual_y_nombres_propios(self):
        for texto in (
            "juan viene manana",
            "hablo con maria",
            "pedro esta aqui",
            "me gusta la musica",
            "que tal tu dia",
        ):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "desconocido")

    def test_frases_con_hola(self):
        self.assert_intencion("hola, como estas", "saludo")
        self.assert_intencion("hola me llamo pedro", "saludo")
        self.assert_intencion("holandes", "desconocido")

    def test_negacion_de_salir_no_apaga(self):
        for texto in ("no quiero salir", "nunca quiero salir", "no me salgas con eso"):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "desconocido")


if __name__ == "__main__":
    unittest.main()