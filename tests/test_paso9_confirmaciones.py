import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import core.cerebro as cerebro
from core.continuacion import (
    ContinuadorConfirmaciones,
    es_afirmacion,
    es_negacion,
)
from core.ejecutor import EjecutorPlan
from core.tools.contratos import (
    POLITICA_AUTO,
    POLITICA_CONFIRMAR,
    Parametro,
    Tool,
    ToolResult,
)
from core.tools.registro import ToolRegistry
from ia.contratos import RespuestaIA
from utilidades.rutas import configurar_base_datos


_NAVEGADOR_PARAMS = (
    Parametro("consulta", requerido=False, tipo=str, descripcion="Busqueda."),
    Parametro("aplicacion", requerido=False, tipo=str, descripcion="Aplicacion."),
)
_APLICACION_PARAMS = (
    Parametro("aplicacion", requerido=True, tipo=str, descripcion="Aplicacion."),
    Parametro("config", requerido=False, tipo=dict, descripcion="Configuracion."),
)

_CONFIG = {"ia": {"activada": False}}


def _tool(nombre, politica, ejecutor, parametros=()) -> Tool:
    return Tool(
        name=nombre,
        description=f"Tool {nombre}.",
        ejecutor=ejecutor,
        parametros=parametros,
        politica=politica,
    )


def _fake_ejecutor(llamados, mensaje, nombre, exito=True):
    def _ejecutar(**kwargs):
        llamados.append(kwargs)
        if exito:
            return ToolResult(True, mensaje, nombre)
        return ToolResult(
            False,
            f"No pude ejecutar {nombre}.",
            nombre,
            error=f"Fallo al ejecutar {nombre}.",
        )

    return _ejecutar


def _registro_con(overrides) -> ToolRegistry:
    registro = ToolRegistry()
    registro._asegurar_base()
    for nombre, tool in overrides.items():
        registro._tools[nombre] = tool
    return registro


def _preparar_cerebro(overrides):
    registro = _registro_con(overrides)
    ejecutor = EjecutorPlan(registro)
    cont = ContinuadorConfirmaciones(ejecutor=EjecutorPlan(registro))
    parche = mock.patch.multiple(
        "core.cerebro",
        _EJECUTOR_PLAN=ejecutor,
        CONTINUADOR=cont,
    )
    return cont, parche


def _procesar(frase, overrides, memoria=None, config=None):
    cont, parche = _preparar_cerebro(overrides)
    with parche:
        resultado = cerebro.procesar(
            frase,
            memoria if memoria is not None else {},
            config if config is not None else _CONFIG,
        )
    return cont, resultado


class InterpretacionTests(unittest.TestCase):
    def test_afirmaciones_reconocidas(self):
        for respuesta in ("si", "sí", "s", "confirmar", "adelante", "ok", "vale", "claro"):
            with self.subTest(respuesta=respuesta):
                self.assertTrue(es_afirmacion(respuesta))
                self.assertFalse(es_negacion(respuesta))

    def test_negaciones_reconocidas(self):
        for respuesta in ("no", "n", "cancelar", "cancela", "detener", "detén"):
            with self.subTest(respuesta=respuesta):
                self.assertTrue(es_negacion(respuesta))
                self.assertFalse(es_afirmacion(respuesta))

    def test_respuesta_invalida_no_es_nada(self):
        for respuesta in ("bailar", "quizas", "tal vez", "123"):
            with self.subTest(respuesta=respuesta):
                self.assertFalse(es_afirmacion(respuesta))
                self.assertFalse(es_negacion(respuesta))


class PoliticaEnCerebroTests(unittest.TestCase):
    def setUp(self):
        self.nav = []

    def test_auto_no_pide_confirmacion(self):
        overrides = {
            "abrir_aplicacion": _tool(
                "abrir_aplicacion",
                POLITICA_AUTO,
                _fake_ejecutor(self.nav, "Abriendo Chrome.", "abrir_aplicacion"),
                _APLICACION_PARAMS,
            ),
            "listar_aplicaciones": _tool(
                "listar_aplicaciones",
                POLITICA_AUTO,
                _fake_ejecutor(self.nav, "Aplicaciones listadas.", "listar_aplicaciones"),
            ),
        }
        cont, resultado = _procesar("abre Chrome y lista aplicaciones", overrides)

        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertIsNone(resultado.solicitud)
        self.assertIsNone(resultado.solicitud_pendiente)
        self.assertEqual(len(self.nav), 2)

    def test_confirmar_genera_solicitud(self):
        overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(self.nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }
        cont, resultado = _procesar("busca gatos", overrides)

        self.assertIsNotNone(resultado.solicitud)
        self.assertEqual(resultado.solicitud["tipo"], "confirmar_politica")
        self.assertIsNotNone(resultado.solicitud_pendiente)
        self.assertEqual(self.nav, [])

    def test_solicitud_contiene_tool(self):
        overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(self.nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }
        cont, resultado = _procesar("busca gatos", overrides)

        self.assertEqual(resultado.solicitud["tool"], "abrir_navegador")

    def test_solicitud_contiene_paso(self):
        overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(self.nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }
        cont, resultado = _procesar("busca gatos", overrides)

        self.assertIn("paso", resultado.solicitud)
        self.assertEqual(resultado.solicitud["paso"], 0)

    def test_solicitud_contiene_parametros(self):
        overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(self.nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }
        cont, resultado = _procesar("busca gatos", overrides)

        self.assertEqual(resultado.solicitud["parametros"], {"consulta": "gatos"})


class ContinuarSolicitudTests(unittest.TestCase):
    def setUp(self):
        self.nav = []
        self.overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(self.nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }

    def test_usuario_confirma_ejecuta(self):
        cont, resultado = _procesar("busca gatos", self.overrides)

        continuado = cont.continuar(resultado.solicitud, True, _CONFIG)

        self.assertEqual(len(self.nav), 1)
        self.assertEqual(continuado.accion, "ejecutar_plan")
        self.assertIn("Navegador abierto.", continuado.respuesta)
        self.assertEqual(continuado.debug["ejecucion"]["ejecutados"], 1)

    def test_usuario_rechaza_no_ejecuta(self):
        cont, resultado = _procesar("busca gatos", self.overrides)

        continuado = cont.continuar(resultado.solicitud, False, _CONFIG)

        self.assertEqual(self.nav, [])
        self.assertEqual(continuado.accion, "confirmacion_cancelada")
        self.assertEqual(continuado.respuesta, "Cancelado.")

    def test_respuesta_invalida_vuelve_a_pedir(self):
        from main import _atender_confirmacion_politica

        cont, resultado = _procesar("busca gatos", self.overrides)
        with mock.patch("core.continuacion.CONTINUADOR", cont), mock.patch(
            "builtins.input", side_effect=["bailar", "quizas", "si"]
        ):
            continuado = _atender_confirmacion_politica(resultado.solicitud, _CONFIG)

        self.assertEqual(len(self.nav), 1)
        self.assertEqual(continuado.accion, "ejecutar_plan")
        self.assertIn("Navegador abierto.", continuado.respuesta)


class MultipasoTests(unittest.TestCase):
    def setUp(self):
        self.abrir = []
        self.nav = []
        self.listar = []
        self.overrides = {
            "abrir_aplicacion": _tool(
                "abrir_aplicacion",
                POLITICA_AUTO,
                _fake_ejecutor(self.abrir, "Abriendo Chrome.", "abrir_aplicacion"),
                _APLICACION_PARAMS,
            ),
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(self.nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
            "listar_aplicaciones": _tool(
                "listar_aplicaciones",
                POLITICA_AUTO,
                _fake_ejecutor(self.listar, "Aplicaciones listadas.", "listar_aplicaciones"),
            ),
        }
        self.frase = "abre Chrome, busca gatos y lista aplicaciones"

    def test_confirmacion_no_reejecuta_pasos_anteriores(self):
        cont, resultado = _procesar(self.frase, self.overrides)
        self.assertEqual(len(self.abrir), 1)
        self.assertEqual(self.nav, [])
        self.assertEqual(self.listar, [])

        continuado = cont.continuar(resultado.solicitud, True, _CONFIG)

        self.assertEqual(len(self.abrir), 1)
        self.assertEqual(len(self.nav), 1)
        self.assertEqual(len(self.listar), 1)
        self.assertEqual(continuado.respuesta.count("Abriendo Chrome."), 1)
        self.assertIn("Navegador abierto.", continuado.respuesta)
        self.assertIn("Aplicaciones listadas.", continuado.respuesta)

    def test_confirmacion_ejecuta_exactamente_el_paso_pendiente(self):
        cont, resultado = _procesar("abre Chrome y busca gatos", self.overrides)

        continuado = cont.continuar(resultado.solicitud, True, _CONFIG)

        self.assertEqual(len(self.abrir), 1)
        self.assertEqual(len(self.nav), 1)
        self.assertEqual(self.listar, [])
        self.assertEqual(continuado.debug["ejecucion"]["ejecutados"], 1)
        self.assertEqual(
            continuado.respuesta,
            "Abriendo Chrome.\nNavegador abierto.",
        )

    def test_plan_multipaso_continua_despues_de_confirmar(self):
        cont, resultado = _procesar(self.frase, self.overrides)

        continuado = cont.continuar(resultado.solicitud, True, _CONFIG)

        self.assertEqual(len(self.nav), 1)
        self.assertEqual(len(self.listar), 1)
        self.assertEqual(continuado.debug["ejecucion"]["ejecutados"], 2)
        self.assertEqual(
            continuado.respuesta,
            "Abriendo Chrome.\nNavegador abierto.\nAplicaciones listadas.",
        )

    def test_plan_multipaso_no_continua_despues_de_rechazar(self):
        cont, resultado = _procesar(self.frase, self.overrides)

        continuado = cont.continuar(resultado.solicitud, False, _CONFIG)

        self.assertEqual(self.nav, [])
        self.assertEqual(self.listar, [])
        self.assertEqual(continuado.accion, "confirmacion_cancelada")

    def test_fallo_despues_de_confirmar_bloquea_los_siguientes(self):
        overrides = dict(self.overrides)
        overrides["abrir_navegador"] = _tool(
            "abrir_navegador",
            POLITICA_CONFIRMAR,
            _fake_ejecutor(
                self.nav,
                "No pude abrir el navegador.",
                "abrir_navegador",
                exito=False,
            ),
            _NAVEGADOR_PARAMS,
        )

        cont, resultado = _procesar(self.frase, overrides)

        continuado = cont.continuar(resultado.solicitud, True, _CONFIG)

        self.assertEqual(len(self.nav), 1)
        self.assertEqual(self.listar, [])
        self.assertEqual(continuado.debug["ejecucion"]["fallidos"], 1)
        self.assertEqual(continuado.debug["ejecucion"]["bloqueados"], 1)


class ProteccionesTests(unittest.TestCase):
    def test_solicitud_consumida_no_puede_ejecutarse_dos_veces(self):
        nav = []
        overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }
        cont, resultado = _procesar("busca gatos", overrides)
        solicitud = resultado.solicitud

        primero = cont.continuar(solicitud, True, _CONFIG)
        segundo = cont.continuar(solicitud, True, _CONFIG)

        self.assertEqual(len(nav), 1)
        self.assertEqual(primero.accion, "ejecutar_plan")
        self.assertEqual(segundo.accion, "solicitud_consumida")
        self.assertEqual(segundo.respuesta, "Esa solicitud ya fue respondida.")

    def test_solicitud_antigua_no_se_reutiliza_despues_de_otro_comando(self):
        nav = []
        overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }
        cont, parche = _preparar_cerebro(overrides)
        with parche:
            resultado = cerebro.procesar("busca gatos", {}, _CONFIG)
            solicitud_antigua = resultado.solicitud
            cerebro.procesar("hola", {}, _CONFIG)

        continuado = cont.continuar(solicitud_antigua, True, _CONFIG)

        self.assertEqual(nav, [])
        self.assertEqual(continuado.accion, "solicitud_obsoleta")
        self.assertEqual(continuado.respuesta, "Esa solicitud ya no esta vigente.")

    def test_solicitud_de_otro_tipo_se_rechaza(self):
        nav = []
        overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }
        cont, resultado = _procesar("busca gatos", overrides)
        solicitud = dict(resultado.solicitud)
        solicitud["tipo"] = "confirmar_accion_pc"

        continuado = cont.continuar(solicitud, True, _CONFIG)

        self.assertEqual(nav, [])
        self.assertEqual(continuado.accion, "solicitud_invalida")


class RutaUnicaTests(unittest.TestCase):
    def test_la_continuacion_usa_toolregistry_como_unica_via(self):
        nav = []
        overrides = {
            "abrir_navegador": _tool(
                "abrir_navegador",
                POLITICA_CONFIRMAR,
                _fake_ejecutor(nav, "Navegador abierto.", "abrir_navegador"),
                _NAVEGADOR_PARAMS,
            ),
        }
        cont, resultado = _procesar("busca gatos", overrides)

        with mock.patch(
            "core.cerebro.ejecutar_herramienta",
            side_effect=AssertionError("no debe usarse la via antigua"),
        ):
            continuado = cont.continuar(resultado.solicitud, True, _CONFIG)

        self.assertEqual(len(nav), 1)
        self.assertEqual(continuado.accion, "ejecutar_plan")

    def test_ejecutoraccionespc_sigue_siendo_respetado(self):
        from core.tools.herramientas.aplicaciones import abrir_aplicacion

        nav = []
        overrides = {
            "abrir_aplicacion": _tool(
                "abrir_aplicacion",
                POLITICA_CONFIRMAR,
                abrir_aplicacion,
                _APLICACION_PARAMS,
            ),
        }
        cont, resultado = _procesar("abre Steam", overrides)

        self.assertIsNotNone(resultado.solicitud)
        continuado = cont.continuar(resultado.solicitud, True, _CONFIG)

        self.assertEqual(len(nav), 0)
        self.assertEqual(continuado.accion, "ejecutar_plan")
        self.assertEqual(continuado.debug["ejecucion"]["fallidos"], 1)
        self.assertIn("control del PC", continuado.respuesta)


class CompatibilidadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.memoria = {}
        self.config = {"ia": {"activada": False}}
        from core.memoria import inicializar_memoria

        self.memoria = inicializar_memoria({})

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def test_handlers_antiguos_siguen_funcionando(self):
        resultado = cerebro.procesar("que fecha es", self.memoria, self.config)
        self.assertEqual(resultado.accion, "mostrar_fecha")

        resultado = cerebro.procesar("lista skills", self.memoria, self.config)
        self.assertEqual(resultado.accion, "listar_skills")

        resultado = cerebro.procesar("hola", self.memoria, self.config)
        self.assertEqual(resultado.accion, "saludar")
        self.assertEqual(resultado.acciones, ())

    def test_salir_sigue_funcionando(self):
        resultado = cerebro.procesar("salir", self.memoria, self.config)
        self.assertTrue(resultado.salir)
        self.assertEqual(resultado.accion, "salir")

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_ia_sigue_siendo_ultimo_recurso(self, generar):
        self.config["ia"]["activada"] = True
        generar.return_value = RespuestaIA("Respuesta simulada", "groq")

        resultado = cerebro.procesar("cuentame algo", self.memoria, self.config)

        self.assertEqual(resultado.accion, "respuesta_ia_groq")
        self.assertEqual(resultado.acciones, ())
        generar.assert_called_once()


class ConfirmacionLegacyPCTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        from core.memoria import inicializar_memoria

        self.memoria = inicializar_memoria({})
        self.config = {"ia": {"activada": False}}

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    @mock.patch("core.handlers.aplicaciones.EjecutorAccionesPC")
    def test_confirmacion_antigua_de_ejecutoraccionespc_sigue_funcionando(self, ej_pc):
        from core.cerebro import completar_solicitud
        from servicios.sistema.contratos import ResultadoAccion

        instancia = ej_pc.return_value
        solicitud = {
            "tipo": "confirmar_accion_pc",
            "identificador": "Chrome",
            "accion": "cerrar_aplicacion",
            "parametros": {"aplicacion": "Chrome"},
            "texto_confirmacion": "Quieres ejecutar cerrar una aplicacion registrada?",
        }
        instancia.preparar.return_value = (None, solicitud)

        resultado = cerebro.procesar("cierra Chrome", self.memoria, self.config)

        self.assertIsInstance(resultado.solicitud_pendiente, dict)
        self.assertEqual(resultado.solicitud_pendiente["tipo"], "confirmar_accion_pc")

        instancia.ejecutar.return_value = ResultadoAccion(
            exito=True,
            mensaje="Chrome cerrado.",
            accion="cerrar_aplicacion",
        )
        confirmado = completar_solicitud(
            resultado.solicitud_pendiente,
            "si",
            self.memoria,
            self.config,
        )
        self.assertEqual(confirmado.accion, "cerrar_aplicacion")
        self.assertEqual(confirmado.respuesta, "Chrome cerrado.")


if __name__ == "__main__":
    unittest.main()