import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.interprete import analizar
from core.memoria import inicializar_memoria
from core.planificador import planificar
from core.tools import ejecutar_herramienta
from core.tools.herramientas.navegador import abrir_navegador
from servicios.sistema.contratos import ResultadoAccion
from utilidades.rutas import configurar_base_datos


class ContratoNavegadorTests(unittest.TestCase):
    """Contrato de la Tool: consulta estructurada -> busqueda/navegacion."""

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_consulta_generica_abre_una_busqueda_web(self, abrir):
        resultado = abrir_navegador(consulta="gatos")

        self.assertTrue(resultado.exito)
        self.assertEqual(resultado.mensaje, "Navegador abierto.")
        self.assertEqual(resultado.datos, {"consulta": "gatos"})
        abrir.assert_called_once_with("https://google.com/search?q=gatos")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_consulta_youtube_navega_a_youtube(self, abrir):
        resultado = abrir_navegador(consulta="youtube")

        self.assertTrue(resultado.exito)
        self.assertEqual(resultado.mensaje, "Navegador abierto.")
        abrir.assert_called_once_with("https://youtube.com")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_consulta_compuesta_se_conserva_entera(self, abrir):
        resultado = abrir_navegador(consulta="rock y roll")

        self.assertTrue(resultado.exito)
        abrir.assert_called_once_with("https://google.com/search?q=rock+y+roll")

    def test_consulta_vacia_no_abre_navegador(self):
        resultado = abrir_navegador()

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "error_navegador")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=False)
    def test_busqueda_falla_si_el_navegador_no_esta_disponible(self, abrir):
        resultado = abrir_navegador(consulta="gatos")

        self.assertFalse(resultado.exito)
        self.assertIn("Fallo al abrir el navegador.", resultado.error)


class PropagacionConsultaTests(unittest.TestCase):
    def test_planifica_la_consulta_como_dato_estructurado(self):
        paso = planificar(analizar("busca gatos")).pasos[0]

        self.assertEqual(paso.estado, "planificable")
        self.assertEqual(paso.tool, "abrir_navegador")
        self.assertEqual(paso.parametros, {"consulta": "gatos"})

    def test_planifica_consulta_compuesta_sin_partirla(self):
        paso = planificar(analizar("busca rock y roll")).pasos[0]

        self.assertEqual(paso.tool, "abrir_navegador")
        self.assertEqual(paso.parametros, {"consulta": "rock y roll"})

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_la_consulta_viaja_al_navegador_sin_reinterpretarse(self, abrir):
        resultado = ejecutar_herramienta("abrir_navegador", {"consulta": "gatos"})

        self.assertTrue(resultado.exito)
        abrir.assert_called_once_with("https://google.com/search?q=gatos")


class IntegracionCerebroTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"ia": {"activada": False}}

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_abre_brave_y_busca_youtube_en_orden(self, abrir):
        with mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC") as ej_pc:
            instancia = ej_pc.return_value
            instancia.preparar.return_value = (
                ResultadoAccion(exito=True, mensaje="Abriendo Brave.", accion="abrir_aplicacion"),
                None,
            )

            resultado = procesar("abre brave y busca youtube", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(
            resultado.respuestas,
            ("Abriendo Brave.", "Navegador abierto."),
        )
        self.assertEqual(
            resultado.respuesta,
            "Abriendo Brave.\nNavegador abierto.",
        )
        self.assertEqual(resultado.debug["ejecucion"]["ejecutados"], 2)
        abrir.assert_called_once_with("https://youtube.com")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_abre_chrome_y_luego_busca_gatos_en_orden(self, abrir):
        with mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC") as ej_pc:
            instancia = ej_pc.return_value
            instancia.preparar.return_value = (
                ResultadoAccion(exito=True, mensaje="Abriendo Chrome.", accion="abrir_aplicacion"),
                None,
            )

            resultado = procesar("abre chrome y luego busca gatos", self.memoria, self.config)

        self.assertEqual(
            resultado.respuestas,
            ("Abriendo Chrome.", "Navegador abierto."),
        )
        abrir.assert_called_once_with("https://google.com/search?q=gatos")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_busca_gatos_abre_el_navegador(self, abrir):
        resultado = procesar("busca gatos", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.respuesta, "Navegador abierto.")
        self.assertEqual(resultado.acciones[0].tool, "abrir_navegador")
        abrir.assert_called_once_with("https://google.com/search?q=gatos")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_busca_rock_y_roll_conserva_la_consulta(self, abrir):
        resultado = procesar("busca rock y roll", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.respuesta, "Navegador abierto.")
        self.assertEqual(resultado.acciones[0].parametros, {"consulta": "rock y roll"})
        abrir.assert_called_once_with("https://google.com/search?q=rock+y+roll")


class BloqueoYPermisosTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"ia": {"activada": False}}

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_si_el_primer_paso_falla_la_busqueda_no_se_ejecuta(self, ej_pc, abrir):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(
                exito=False,
                mensaje="El control del PC esta desactivado.",
                accion="abrir_aplicacion",
                tipo_error="accion_no_permitida",
            ),
            None,
        )

        resultado = procesar("abre brave y busca youtube", self.memoria, self.config)

        self.assertEqual(resultado.debug["ejecucion"]["fallidos"], 1)
        self.assertEqual(resultado.debug["ejecucion"]["bloqueados"], 1)
        self.assertIn("El control del PC esta desactivado.", resultado.respuesta)
        abrir.assert_not_called()

    @mock.patch("comandos.navegador.webbrowser.open", return_value=False)
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_si_la_busqueda_falla_el_primer_paso_conserva_su_resultado(self, ej_pc, abrir):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Brave.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre brave y busca youtube", self.memoria, self.config)

        self.assertEqual(
            resultado.respuestas,
            ("Abriendo Brave.", "Fallo al abrir el navegador."),
        )
        self.assertIn("Abriendo Brave.", resultado.respuesta)
        self.assertEqual(resultado.debug["ejecucion"]["fallidos"], 1)

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    @mock.patch("core.cerebro.ejecutar_herramienta")
    def test_la_busqueda_usa_toolregistry_y_no_el_helper_directo(self, ejecutar, ej_pc, abrir):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Brave.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre brave y busca youtube", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(len(resultado.respuestas), 2)
        ejecutar.assert_not_called()
        ej_pc.assert_called_once()
        abrir.assert_called_once_with("https://youtube.com")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_los_permisos_existentes_siguen_funcionando(self, ej_pc, abrir):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Brave.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre brave y busca youtube", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        ej_pc.assert_called_once_with(self.config)
        instancia.preparar.assert_called_once_with(
            "abrir_aplicacion",
            {"aplicacion": "brave"},
        )
        abrir.assert_called_once_with("https://youtube.com")


if __name__ == "__main__":
    unittest.main()