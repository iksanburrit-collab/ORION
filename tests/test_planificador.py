import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.interprete import TIPO_OBJETO, RegistroVerbos, Verbo, analizar
from core.planificador import (
    ESTADO_ENTIDAD_INCOMPATIBLE,
    ESTADO_ENTIDAD_INSUFICIENTE,
    ESTADO_NO_PLANIFICABLE,
    ESTADO_PLANIFICABLE,
    ESTADO_SIN_TOOL,
    planificar,
)
from core.tools.contratos import Parametro, Tool, ToolResult


class RegistroStub:
    """Sustituto de ToolRegistry que registra las llamadas para espiar."""

    def __init__(self, tools):
        self._tools = dict(tools)
        self.llamadas_obtener = []
        self.llamadas_ejecutar = []

    def existe(self, nombre):
        return nombre in self._tools

    def obtener(self, nombre):
        self.llamadas_obtener.append(nombre)
        return self._tools[nombre]

    def ejecutar(self, nombre, parametros=None):
        self.llamadas_ejecutar.append((nombre, parametros))
        return ToolResult(exito=True, mensaje="ok", tool=nombre)


class PlanificadorOperacionesSimplesTests(unittest.TestCase):
    def test_abre_steam_es_planificable(self):
        plan = planificar(analizar("abre Steam"))
        self.assertTrue(plan.reconocido)
        self.assertTrue(plan.resoluble)
        self.assertEqual(len(plan.pasos), 1)

        paso = plan.pasos[0]
        self.assertEqual(paso.estado, ESTADO_PLANIFICABLE)
        self.assertEqual(paso.tool, "abrir_aplicacion")
        self.assertEqual(paso.parametros, {"aplicacion": "Steam"})
        self.assertEqual(paso.verbo, "abrir")

    def test_inicia_steam_usa_abrir_aplicacion(self):
        paso = planificar(analizar("inicia Steam")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_PLANIFICABLE)
        self.assertEqual(paso.tool, "abrir_aplicacion")
        self.assertEqual(paso.parametros, {"aplicacion": "Steam"})

    def test_busca_youtube_usa_abrir_navegador(self):
        paso = planificar(analizar("busca YouTube")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_PLANIFICABLE)
        self.assertEqual(paso.tool, "abrir_navegador")
        self.assertEqual(paso.parametros, {"consulta": "YouTube"})

    def test_abre_con_nombre_varias_palabras(self):
        paso = planificar(analizar("abre Visual Studio Code")).pasos[0]
        self.assertEqual(paso.parametros, {"aplicacion": "Visual Studio Code"})

    def test_lista_aplicaciones_es_planificable(self):
        paso = planificar(analizar("lista aplicaciones")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_PLANIFICABLE)
        self.assertEqual(paso.tool, "listar_aplicaciones")
        self.assertEqual(paso.parametros, {})

    def test_orden_y_texto_del_paso(self):
        plan = planificar(analizar("abre Chrome y busca gatos"))
        primera, segunda = plan.pasos
        self.assertEqual(primera.orden, 0)
        self.assertEqual(primera.texto, "abre Chrome")
        self.assertEqual(segunda.orden, 1)
        self.assertEqual(segunda.texto, "busca gatos")


class PlanificadorSinToolTests(unittest.TestCase):
    def test_cierra_steam_sin_tool(self):
        paso = planificar(analizar("cierra Steam")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_SIN_TOOL)
        self.assertIsNone(paso.tool)
        self.assertEqual(paso.parametros, {})

    def test_ejecuta_pruebas_sin_tool(self):
        paso = planificar(analizar("ejecuta las pruebas")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_SIN_TOOL)
        self.assertIsNone(paso.tool)

    def test_crea_tarea_sin_tool(self):
        paso = planificar(analizar("crea tarea")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_SIN_TOOL)
        self.assertIsNone(paso.tool)

    def test_dime_que_juegos_sin_tool(self):
        paso = planificar(analizar("dime que juegos tengo instalados")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_SIN_TOOL)
        self.assertIsNone(paso.tool)


class PlanificadorEntidadTests(unittest.TestCase):
    def test_abre_mi_proyecto_orion_incompatible(self):
        paso = planificar(analizar("abre mi proyecto ORION")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_ENTIDAD_INCOMPATIBLE)
        self.assertEqual(paso.tool, "abrir_aplicacion")
        self.assertEqual(paso.parametros, {})

    def test_lista_tareas_incompatible(self):
        paso = planificar(analizar("lista tareas")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_ENTIDAD_INCOMPATIBLE)
        self.assertEqual(paso.tool, "listar_aplicaciones")

    def test_abre_sin_entidad_insuficiente(self):
        paso = planificar(analizar("abre")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_ENTIDAD_INSUFICIENTE)
        self.assertEqual(paso.tool, "abrir_aplicacion")
        self.assertEqual(paso.parametros, {})

    def test_busca_sin_entidad_insuficiente(self):
        paso = planificar(analizar("busca")).pasos[0]
        self.assertEqual(paso.estado, ESTADO_ENTIDAD_INSUFICIENTE)
        self.assertEqual(paso.tool, "abrir_navegador")


class PlanificadorVerboNoMapeadoTests(unittest.TestCase):
    def test_verbo_fuera_del_mapa_no_planificable(self):
        registro = RegistroVerbos(
            (Verbo("volar", ("vuela", "volar"), TIPO_OBJETO),)
        )
        plan = planificar(analizar("vuela alto", registro_verbos=registro))
        self.assertTrue(plan.reconocido)
        self.assertFalse(plan.resoluble)

        paso = plan.pasos[0]
        self.assertEqual(paso.estado, ESTADO_NO_PLANIFICABLE)
        self.assertIsNone(paso.tool)


class PlanificadorCompuestoTests(unittest.TestCase):
    def test_abre_steam_y_dime_conserva_ambos_pasos(self):
        plan = planificar(
            analizar("abre Steam y dime qué juegos tengo instalados")
        )
        self.assertEqual(len(plan.pasos), 2)

        primera, segunda = plan.pasos
        self.assertEqual(primera.estado, ESTADO_PLANIFICABLE)
        self.assertEqual(primera.tool, "abrir_aplicacion")
        self.assertEqual(primera.parametros, {"aplicacion": "Steam"})

        self.assertEqual(segunda.estado, ESTADO_SIN_TOOL)
        self.assertEqual(segunda.verbo, "consultar")
        self.assertIsNone(segunda.tool)

        self.assertTrue(plan.resoluble)

    def test_plan_con_dos_pasos_planificables(self):
        plan = planificar(analizar("abre Chrome y busca gatos"))
        self.assertTrue(plan.resoluble)
        self.assertEqual(
            [paso.estado for paso in plan.pasos],
            [ESTADO_PLANIFICABLE, ESTADO_PLANIFICABLE],
        )

    def test_errores_recolectan_motivos(self):
        plan = planificar(
            analizar("abre Steam y dime qué juegos tengo instalados")
        )
        self.assertEqual(len(plan.errores), 1)
        self.assertIn("consultar", plan.errores[0])

    def test_advertencias_con_fragmentos_no_reconocidos(self):
        plan = planificar(analizar("por favor abre Chrome y busca gatos"))
        self.assertEqual(plan.advertencias, ("por favor abre Chrome",))
        self.assertEqual(len(plan.pasos), 1)


class PlanificadorHelpersTests(unittest.TestCase):
    def test_pasos_planificables_y_no(self):
        plan = planificar(
            analizar("abre Steam y dime qué juegos tengo instalados")
        )
        planificables = plan.pasos_planificables()
        no_planificables = plan.pasos_no_planificables()

        self.assertEqual(len(planificables), 1)
        self.assertEqual(len(no_planificables), 1)
        self.assertEqual(planificables[0].verbo, "abrir")
        self.assertEqual(no_planificables[0].verbo, "consultar")

    def test_metadatos_cantidad_de_pasos(self):
        plan = planificar(analizar("abre Chrome y busca gatos"))
        self.assertEqual(plan.metadatos["cantidad_pasos"], 2)


class PlanificadorPlanVacioTests(unittest.TestCase):
    def test_plan_sin_analisis(self):
        plan = planificar()
        self.assertFalse(plan.reconocido)
        self.assertFalse(plan.resoluble)
        self.assertEqual(plan.pasos, ())
        self.assertEqual(plan.errores, ())

    def test_analisis_no_reconocido(self):
        plan = planificar(analizar("hola"))
        self.assertFalse(plan.reconocido)
        self.assertFalse(plan.resoluble)
        self.assertEqual(plan.pasos, ())

    def test_planificacion_de_vacio(self):
        plan = planificar(analizar(""))
        self.assertEqual(plan.pasos, ())
        self.assertEqual(plan.metadatos["cantidad_pasos"], 0)


class PlanificadorSinEjecucionTests(unittest.TestCase):
    def test_no_ejecuta_la_tool_al_planificar(self):
        ejecutado = []

        def ejecutor(**kwargs):
            ejecutado.append(kwargs)
            return ToolResult(exito=True, mensaje="ok", tool="abrir_aplicacion")

        tool = Tool(
            name="abrir_aplicacion",
            description="Tool de prueba.",
            ejecutor=ejecutor,
            parametros=(Parametro("aplicacion", requerido=True, tipo=str),),
        )
        registro = RegistroStub({"abrir_aplicacion": tool})

        plan = planificar(analizar("abre Steam"), registro=registro)

        paso = plan.pasos[0]
        self.assertEqual(paso.estado, ESTADO_PLANIFICABLE)
        self.assertEqual(paso.parametros, {"aplicacion": "Steam"})
        self.assertEqual(registro.llamadas_ejecutar, [])
        self.assertEqual(ejecutado, [])
        self.assertEqual(registro.llamadas_obtener, ["abrir_aplicacion"])

    def test_tool_no_registrada_es_sin_tool(self):
        registro = RegistroStub({"abrir_navegador": None})
        paso = planificar(analizar("abre Steam"), registro=registro).pasos[0]
        self.assertEqual(paso.estado, ESTADO_SIN_TOOL)
        self.assertIsNone(paso.tool)


class PlanificadorRegistroRealTests(unittest.TestCase):
    def test_integracion_con_toolregistry_real(self):
        from core.tools.registro import ToolRegistry

        registro = ToolRegistry()
        plan = planificar(analizar("abre Steam"), registro=registro)

        paso = plan.pasos[0]
        self.assertEqual(paso.estado, ESTADO_PLANIFICABLE)
        self.assertEqual(paso.tool, "abrir_aplicacion")
        self.assertEqual(paso.parametros, {"aplicacion": "Steam"})


if __name__ == "__main__":
    unittest.main()