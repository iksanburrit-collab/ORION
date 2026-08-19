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

    def test_fecha_y_hora_se_detectan_con_lenguaje_natural(self):
        casos = {
            "fecha": "fecha",
            "qué fecha es": "fecha",
            "qué fecha es hoy": "fecha",
            "cuál es la fecha de hoy": "fecha",
            "qué día es hoy": "fecha",
            "qué día estamos": "fecha",
            "dime la fecha": "fecha",
            "qué hora es": "hora",
            "dime la hora": "hora",
            "qué hora tenemos": "hora",
        }
        for texto, esperada in casos.items():
            with self.subTest(texto=texto):
                self.assert_intencion(texto, esperada)

    def test_variantes_naturales_de_fecha_y_hora(self):
        casos = {
            "cuál es la fecha": "fecha",
            "cual es la fecha": "fecha",
            "cuál es el día de hoy": "fecha",
            "me dices la fecha": "fecha",
            "qué día es": "fecha",
            "que dia es": "fecha",
            "sabes qué día es hoy": "fecha",
            "me dices la hora": "hora",
            "dime qué hora es": "hora",
            "qué hora es ahora": "hora",
            "qué hora tenemos ahora": "hora",
            "sabes qué hora es": "hora",
            "cuál es la hora": "hora",
        }
        for texto, esperada in casos.items():
            with self.subTest(texto=texto):
                self.assert_intencion(texto, esperada)

    def test_normalizacion_de_voz_aplica_a_todas_las_intenciones(self):
        casos = {
            "  ¿Qué   hora  es?  ": "hora",
            "¿Me dices la hora?": "hora",
            "Me dices la hora.": "hora",
            "¿CUÁL ES LA FECHA?": "fecha",
            "qué fecha es hoy.": "fecha",
            "HOLA": "saludo",
            "¿Ayuda?": "ayuda",
            "2 + 2.": "calc",
        }
        for texto, esperada in casos.items():
            with self.subTest(texto=texto):
                self.assert_intencion(texto, esperada)

    def test_fecha_y_hora_toleran_puntuacion_de_whisper(self):
        casos = {
            "¿qué fecha es hoy?": "fecha",
            "¡Qué fecha es hoy!": "fecha",
            "qué fecha es hoy.": "fecha",
            "¿Qué fecha es hoy?": "fecha",
            "¿qué hora es?": "hora",
            "¡Qué hora es!": "hora",
            "dime la hora.": "hora",
            "¿Qué día es hoy?": "fecha",
            "cuál es la fecha de hoy?": "fecha",
        }
        for texto, esperada in casos.items():
            with self.subTest(texto=texto):
                self.assert_intencion(texto, esperada)

    def test_fecha_y_hora_no_disparan_falsos_positivos(self):
        for texto in (
            "que fecha tiene tu cumpleaños",
            "a que hora empieza la pelicula",
            "cuentame de tu dia",
            "que tan dia es hoy",
        ):
            with self.subTest(texto=texto):
                self.assert_intencion(texto, "desconocido")


if __name__ == "__main__":
    unittest.main()