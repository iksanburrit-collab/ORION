import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.memoria import inicializar_memoria
from ia.contratos import RespuestaIA
from servicios.sistema.contratos import ResultadoAccion
from utilidades.rutas import configurar_base_datos


class Paso4PlanificacionCerebroTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"ia": {"activada": False}}

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()


class ComandoSimpleTests(Paso4PlanificacionCerebroTests):
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_abre_steam_ejecuta_la_tool(self, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Steam.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertTrue(resultado.reconocido)
        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(len(resultado.acciones), 1)

        paso = resultado.acciones[0]
        self.assertEqual(paso.verbo, "abrir")
        self.assertEqual(paso.entidad.valor, "Steam")
        self.assertEqual(paso.tool, "abrir_aplicacion")
        self.assertEqual(paso.parametros, {"aplicacion": "Steam"})
        self.assertEqual(resultado.respuesta, "Abriendo Steam.")
        ej_pc.assert_called_once()


class ComandoCompuestoTests(Paso4PlanificacionCerebroTests):
    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_abre_chrome_y_busca_youtube_ejecuta_ambas_en_orden(self, ej_pc, abrir):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Chrome.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Chrome y busca YouTube", self.memoria, self.config)

        self.assertEqual(len(resultado.acciones), 2)

        primera, segunda = resultado.acciones
        self.assertEqual((primera.verbo, primera.entidad.valor), ("abrir", "Chrome"))
        self.assertEqual(primera.tool, "abrir_aplicacion")
        self.assertEqual((segunda.verbo, segunda.entidad.valor), ("buscar", "YouTube"))
        self.assertEqual(segunda.tool, "abrir_navegador")
        self.assertEqual(
            resultado.respuesta,
            "Abriendo Chrome.\nNavegador abierto.",
        )
        abrir.assert_called_once()

    def test_abre_chrome_despues_busca_gatos(self):
        resultado = procesar("abre Chrome despues busca gatos", self.memoria, self.config)

        self.assertEqual(len(resultado.acciones), 2)
        primera, segunda = resultado.acciones
        self.assertEqual((primera.verbo, primera.entidad.valor), ("abrir", "Chrome"))
        self.assertEqual((segunda.verbo, segunda.entidad.valor), ("buscar", "gatos"))

    def test_abre_chrome_y_luego_busca_gatos(self):
        resultado = procesar("abre Chrome y luego busca gatos", self.memoria, self.config)

        self.assertEqual(len(resultado.acciones), 2)
        self.assertEqual(
            [paso.verbo for paso in resultado.acciones],
            ["abrir", "buscar"],
        )
        self.assertEqual(resultado.acciones[0].entidad.valor, "Chrome")
        self.assertEqual(resultado.acciones[1].entidad.valor, "gatos")

    def test_abre_steam_y_dime_conserva_ambos_pasos(self):
        resultado = procesar(
            "abre Steam y dime qué juegos tengo instalados",
            self.memoria,
            self.config,
        )

        self.assertEqual(len(resultado.acciones), 2)
        self.assertEqual(resultado.acciones[0].tool, "abrir_aplicacion")
        self.assertEqual(resultado.acciones[1].verbo, "consultar")
        self.assertIsNone(resultado.acciones[1].tool)


class EntidadesMultiPalabraTests(Paso4PlanificacionCerebroTests):
    def test_abre_visual_studio_code(self):
        resultado = procesar("abre Visual Studio Code", self.memoria, self.config)

        self.assertEqual(len(resultado.acciones), 1)
        paso = resultado.acciones[0]
        self.assertEqual(paso.entidad.valor, "Visual Studio Code")
        self.assertEqual(paso.parametros, {"aplicacion": "Visual Studio Code"})

    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_abre_vscode_y_luego_abre_mi_proyecto_orion(self, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.side_effect = lambda nombre, parametros: (
            ResultadoAccion(
                exito=True,
                mensaje=f"Abriendo {parametros.get('aplicacion')}.",
                accion=nombre,
            ),
            None,
        )

        resultado = procesar(
            "abre VS Code y luego abre mi proyecto ORION",
            self.memoria,
            self.config,
        )

        self.assertEqual(len(resultado.acciones), 2)

        primera, segunda = resultado.acciones
        self.assertEqual(primera.entidad.valor, "VS Code")
        self.assertEqual(primera.tool, "abrir_aplicacion")
        self.assertEqual(segunda.entidad.valor, "mi proyecto ORION")
        self.assertEqual(resultado.respuesta, "Abriendo VS Code.")
        self.assertEqual(resultado.debug["ejecucion"]["omitidos"], 1)


class IntencionesExistentesTests(Paso4PlanificacionCerebroTests):
    def test_saludo_sigue_el_mecanismo_existente(self):
        resultado = procesar("hola", self.memoria, self.config)

        self.assertEqual(resultado.accion, "saludar")
        self.assertFalse(resultado.reconocido)
        self.assertEqual(resultado.acciones, ())

    def test_salir_sigue_funcionando_exactamente_igual(self):
        resultado = procesar("salir", self.memoria, self.config)

        self.assertTrue(resultado.salir)
        self.assertEqual(resultado.accion, "salir")
        self.assertEqual(resultado.acciones, ())

    def test_calculadora_sigue_funcionando(self):
        resultado = procesar("2 + 3 * 4", self.memoria, self.config)

        self.assertEqual(resultado.accion, "calcular")
        self.assertEqual(resultado.respuesta, "🧮 14")
        self.assertEqual(resultado.acciones, ())


class HandlersAntiguosTests(Paso4PlanificacionCerebroTests):
    def test_lista_skills_sigue_en_el_handler(self):
        resultado = procesar("lista skills", {}, {"ia": {"activada": False}})

        self.assertEqual(resultado.accion, "listar_skills")
        self.assertEqual(resultado.acciones, ())

    def test_que_fecha_es_sigue_en_el_handler(self):
        resultado = procesar("que fecha es", self.memoria, self.config)

        self.assertEqual(resultado.accion, "mostrar_fecha")
        self.assertEqual(resultado.acciones, ())

    def test_cierra_sigue_en_el_handler_por_no_ser_resoluble(self):
        with mock.patch("core.handlers.aplicaciones.EjecutorAccionesPC") as ejecutor:
            ejecutor.return_value.preparar.return_value = (
                None,
                {
                    "identificador": "app",
                    "accion": "cerrar_aplicacion",
                    "texto_confirmacion": "Confirmar.",
                },
            )
            resultado = procesar("cierra app", {}, self.config)

        self.assertNotEqual(resultado.accion, "planificar")
        self.assertEqual(resultado.acciones, ())


class IAUltimoRecursoTests(Paso4PlanificacionCerebroTests):
    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_frase_no_planificada_llega_a_ia(self, generar):
        self.config["ia"]["activada"] = True
        generar.return_value = RespuestaIA("Respuesta simulada", "groq")

        resultado = procesar("cuentame algo", self.memoria, self.config)

        self.assertEqual(resultado.accion, "respuesta_ia_groq")
        self.assertEqual(resultado.acciones, ())
        generar.assert_called_once()

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_frase_planificada_no_llega_a_ia(self, generar):
        self.config["ia"]["activada"] = True
        generar.return_value = RespuestaIA("Respuesta simulada", "groq")

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        generar.assert_not_called()


class EjecucionSeguraTests(Paso4PlanificacionCerebroTests):
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    @mock.patch("core.cerebro.ejecutar_herramienta")
    def test_abre_steam_ejecuta_via_ejecutor_sin_helper_directo(self, ejecutar, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Steam.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.respuesta, "Abriendo Steam.")
        ejecutar.assert_not_called()
        ej_pc.assert_called_once()

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_busca_gatos_ejecuta_una_busqueda_web(self, abrir):
        resultado = procesar("busca gatos", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.respuesta, "Navegador abierto.")
        abrir.assert_called_once()


class NoReconocidaTests(Paso4PlanificacionCerebroTests):
    def test_aprendizaje_sigue_siendo_aprendizaje(self):
        resultado = procesar("me gusta el cafe", self.memoria, self.config)

        self.assertEqual(resultado.accion, "aprendizaje")
        self.assertEqual(resultado.acciones, ())

    def test_frase_vacia_no_genera_plan(self):
        resultado = procesar("", self.memoria, self.config)

        self.assertFalse(resultado.reconocido)
        self.assertEqual(resultado.acciones, ())


if __name__ == "__main__":
    unittest.main()