import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.handlers.contratos import ResultadoCerebro
from core.interprete.contratos import Entidad
from core.memoria import inicializar_memoria
from core.planificador.contratos import ESTADO_PLANIFICABLE, Paso, Plan
from ia.contratos import RespuestaIA
from servicios.sistema.contratos import ResultadoAccion
from utilidades.rutas import configurar_base_datos


def _entidad(valor: str) -> Entidad:
    return Entidad(tipo="objeto", valor=valor, normalizado=valor.lower())


def _plan_con_pasos(*pasos: Paso) -> Plan:
    return Plan(texto_original="", pasos=pasos, reconocido=True, resoluble=True)


def _paso_falso(tool: str | None, parametros: dict | None = None) -> Paso:
    return Paso(
        orden=1,
        verbo="abrir",
        entidad=_entidad("Steam"),
        tool=tool,
        parametros=parametros or {},
        estado=ESTADO_PLANIFICABLE,
        motivo="Planificado.",
        texto="abrir Steam",
    )


class Paso6EjecucionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"ia": {"activada": False}}

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def _abrir_steam(self):
        resultado = procesar("abre Steam", self.memoria, self.config)
        return resultado


class EjecucionDeToolsTests(Paso6EjecucionTests):
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_abre_steam_ejecuta_la_tool(self, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Steam.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertTrue(resultado.reconocido)
        self.assertEqual(resultado.respuesta, "Abriendo Steam.")
        self.assertEqual(resultado.respuestas, ("Abriendo Steam.",))
        self.assertEqual(resultado.debug["ejecucion"]["exito"], True)
        ej_pc.assert_called_once()

    @mock.patch("core.tools.herramientas.navegador.navegador_inteligente", return_value=True)
    @mock.patch("core.tools.herramientas.navegador.es_comando_navegador", return_value=True)
    def test_busca_gatos_ejecuta_la_tool_de_navegador(self, es_comando, navegador):
        resultado = procesar("busca gatos", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.respuesta, "Navegador abierto.")
        self.assertEqual(resultado.acciones[0].tool, "abrir_navegador")
        self.assertEqual(resultado.acciones[0].entidad.valor, "gatos")
        es_comando.assert_called_once_with("gatos")
        navegador.assert_called_once_with("gatos")

    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_abre_chrome_y_busca_youtube_ejecuta_ambas_en_orden(self, ej_pc, abrir):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Chrome.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Chrome y busca YouTube", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.acciones[0].tool, "abrir_aplicacion")
        self.assertEqual(resultado.acciones[1].tool, "abrir_navegador")
        self.assertEqual(
            resultado.respuestas,
            ("Abriendo Chrome.", "Navegador abierto."),
        )
        self.assertEqual(
            resultado.respuesta,
            "Abriendo Chrome.\nNavegador abierto.",
        )
        self.assertEqual(resultado.debug["ejecucion"]["ejecutados"], 2)
        abrir.assert_called_once()


class BloqueoYResultadosTests(Paso6EjecucionTests):
    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_primera_falla_y_la_segunda_no_se_ejecuta(self, ej_pc, abrir):
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

        resultado = procesar("abre Chrome y busca YouTube", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertIn("El control del PC esta desactivado.", resultado.respuesta)
        self.assertEqual(resultado.debug["ejecucion"]["fallidos"], 1)
        self.assertEqual(resultado.debug["ejecucion"]["bloqueados"], 1)
        abrir.assert_not_called()

    @mock.patch("comandos.navegador.webbrowser.open", return_value=False)
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_segunda_falla_y_la_primera_conserva_su_resultado(self, ej_pc, abrir):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Chrome.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Chrome y busca YouTube", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.debug["ejecucion"]["exito"], False)
        self.assertEqual(resultado.debug["ejecucion"]["ejecutados"], 2)
        self.assertEqual(resultado.debug["ejecucion"]["fallidos"], 1)
        self.assertEqual(
            resultado.respuestas,
            ("Abriendo Chrome.", "Fallo al abrir el navegador."),
        )
        self.assertIn("Abriendo Chrome.", resultado.respuesta)


class ErroresClarosTests(Paso6EjecucionTests):
    @mock.patch("core.cerebro.planificar")
    def test_tool_inexistente_devuelve_error_claro(self, planificar):
        planificar.return_value = _plan_con_pasos(_paso_falso("tool_inexistente"))

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertIn("no esta registrada", resultado.respuesta)
        self.assertEqual(resultado.debug["ejecucion"]["fallidos"], 1)
        self.assertEqual(resultado.debug["ejecucion"]["exito"], False)

    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    @mock.patch("core.cerebro.planificar")
    def test_parametros_invalidos_rechaza_sin_ejecutar(self, planificar, ej_pc):
        planificar.return_value = _plan_con_pasos(
            _paso_falso("abrir_aplicacion", parametros={})
        )

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertIn("obligatorio", resultado.respuesta)
        self.assertEqual(resultado.debug["ejecucion"]["fallidos"], 1)
        ej_pc.assert_not_called()


class SeguridadYCompatibilidadTests(Paso6EjecucionTests):
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    @mock.patch("core.cerebro.ejecutar_herramienta")
    def test_no_ejecuta_comandos_fuera_del_toolregistry(self, ejecutar, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Steam.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        ejecutar.assert_not_called()
        ej_pc.assert_called_once()

    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_conserva_la_puerta_ejecutoraccionespc(self, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Steam.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.respuesta, "Abriendo Steam.")
        ej_pc.assert_called_once_with(self.config)
        instancia.preparar.assert_called_once_with(
            "abrir_aplicacion",
            {"aplicacion": "Steam"},
        )

    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_confirmacion_no_se_salta(self, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            None,
            {
                "tipo": "confirmar_accion_pc",
                "identificador": "Steam",
                "accion": "abrir_aplicacion",
                "texto_confirmacion": "Quieres ejecutar abrir una aplicacion registrada?",
            },
        )

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.debug["ejecucion"]["exito"], False)
        self.assertEqual(resultado.debug["ejecucion"]["fallidos"], 1)


class PlanVacioTests(Paso6EjecucionTests):
    @mock.patch("core.cerebro.planificar")
    def test_plan_vacio_no_ejecuta_nada(self, planificar):
        planificar.return_value = _plan_con_pasos()

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertEqual(resultado.acciones, ())
        self.assertEqual(resultado.respuesta, "")
        self.assertEqual(resultado.debug["ejecucion"]["ejecutados"], 0)


class HandlersAntiguosTests(Paso6EjecucionTests):
    def test_comandos_antiguos_siguen_funcionando(self):
        resultado = procesar("que fecha es", self.memoria, self.config)
        self.assertEqual(resultado.accion, "mostrar_fecha")
        self.assertEqual(resultado.acciones, ())

        resultado = procesar("lista skills", {}, {"ia": {"activada": False}})
        self.assertEqual(resultado.accion, "listar_skills")
        self.assertEqual(resultado.acciones, ())

    def test_hola_sigue_funcionando(self):
        resultado = procesar("hola", self.memoria, self.config)

        self.assertEqual(resultado.accion, "saludar")
        self.assertFalse(resultado.reconocido)
        self.assertEqual(resultado.acciones, ())

    def test_salir_sigue_funcionando(self):
        resultado = procesar("salir", self.memoria, self.config)

        self.assertTrue(resultado.salir)
        self.assertEqual(resultado.accion, "salir")
        self.assertEqual(resultado.acciones, ())

    def test_calculadora_sigue_funcionando(self):
        resultado = procesar("2 + 3 * 4", self.memoria, self.config)

        self.assertEqual(resultado.accion, "calcular")
        self.assertEqual(resultado.respuesta, "🧮 14")
        self.assertEqual(resultado.acciones, ())

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_frase_no_planificable_continua_al_flujo_antiguo(self, generar):
        self.config["ia"]["activada"] = True
        generar.return_value = RespuestaIA("Respuesta simulada", "groq")

        resultado = procesar("cuentame algo", self.memoria, self.config)

        self.assertEqual(resultado.accion, "respuesta_ia_groq")
        self.assertEqual(resultado.acciones, ())
        generar.assert_called_once()

    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_resultadocerebro_conserva_compatibilidad(self, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Steam.", accion="abrir_aplicacion"),
            None,
        )

        resultado = procesar("abre Steam", self.memoria, self.config)

        self.assertIsInstance(resultado, ResultadoCerebro)
        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertIsInstance(resultado.respuesta, str)
        self.assertIsNone(resultado.solicitud)
        self.assertIsNone(resultado.solicitud_pendiente)
        self.assertFalse(resultado.salir)
        self.assertIsNone(resultado.conocimiento)
        self.assertIsInstance(resultado.debug, dict)
        self.assertTrue(resultado.reconocido)
        self.assertEqual(len(resultado.acciones), 1)
        self.assertEqual(resultado.respuestas, ("Abriendo Steam.",))


class RespuestaCompuestaTests(Paso6EjecucionTests):
    @mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC")
    def test_respuesta_compuesta_refleja_resultados_reales(self, ej_pc):
        instancia = ej_pc.return_value
        instancia.preparar.return_value = (
            ResultadoAccion(exito=True, mensaje="Abriendo Chrome.", accion="abrir_aplicacion"),
            None,
        )
        with mock.patch("comandos.navegador.webbrowser.open", return_value=True):
            resultado = procesar("abre Chrome y busca YouTube", self.memoria, self.config)

        self.assertEqual(
            resultado.respuesta_compuesta(),
            "Abriendo Chrome.\nNavegador abierto.",
        )
        self.assertEqual(
            resultado.respuesta,
            "\n".join(resultado.respuestas),
        )


if __name__ == "__main__":
    unittest.main()