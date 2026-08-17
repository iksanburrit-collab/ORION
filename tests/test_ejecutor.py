import sys
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.ejecutor import EjecutorPlan
from core.ejecutor.contratos import (
    ESTADO_BLOQUEADO,
    ESTADO_EXITOSO,
    ESTADO_FALLIDO,
    ESTADO_OMITIDO,
    ESTADOS_EJECUCION,
    ResultadoEjecucion,
    ResultadoPaso,
)
from core.interprete.contratos import Entidad
from core.planificador.contratos import (
    ESTADO_PLANIFICABLE,
    ESTADO_SIN_TOOL,
    Paso,
    Plan,
)
from core.tools.contratos import Parametro, Tool, ToolResult
from core.tools.registro import ToolRegistry
from servicios.sistema.contratos import ResultadoAccion


def _entidad(valor: str) -> Entidad:
    return Entidad(tipo="objeto", valor=valor, normalizado=valor.lower())


def _paso(
    orden: int,
    tool: str | None,
    parametros: dict | None = None,
    estado: str = ESTADO_PLANIFICABLE,
    valor: str | None = None,
) -> Paso:
    entidad = _entidad(valor) if valor else None
    return Paso(
        orden=orden,
        verbo="abrir" if tool == "abrir_aplicacion" else "ejecutar",
        entidad=entidad,
        tool=tool,
        parametros=parametros or {},
        estado=estado,
        motivo="Planificado." if estado == ESTADO_PLANIFICABLE else "Paso no ejecutable.",
        texto=f"{valor or 'operacion'} #{orden}",
    )


def _plan(*pasos: Paso) -> Plan:
    return Plan(texto_original="", pasos=pasos, reconocido=True, resoluble=True)


def _tool(nombre: str, ejecutor, parametros: tuple[Parametro, ...] = ()) -> Tool:
    return Tool(
        name=nombre,
        description=f"Tool {nombre}.",
        ejecutor=ejecutor,
        parametros=parametros,
    )


def _registro(*tools: Tool) -> ToolRegistry:
    registro = ToolRegistry()
    for tool in tools:
        registro.registrar(tool)
    return registro


class RegistroStub:
    """Sustituto minimo de ToolRegistry para espiar las llamadas."""

    def __init__(self, tools):
        self._tools = dict(tools)
        self.ejecutados = []

    def existe(self, nombre):
        return nombre in self._tools

    def ejecutar(self, nombre, parametros=None):
        self.ejecutados.append((nombre, parametros or {}))
        return self._tools[nombre].ejecutor(**(parametros or {}))


class ContratosEjecutorTests(unittest.TestCase):
    def test_estados_de_ejecucion_son_los_esperados(self):
        self.assertEqual(
            ESTADOS_EJECUCION,
            ("pendiente", "ejecutado", "exitoso", "fallido", "bloqueado", "omitido"),
        )

    def test_resultado_ejecucion_es_contrato_congelado(self):
        resultado = ResultadoEjecucion(plan=_plan())
        self.assertIsInstance(resultado, ResultadoEjecucion)
        with self.assertRaises(AttributeError):
            resultado.exito = True


class PlanVacioTests(unittest.TestCase):
    def test_plan_vacio_no_ejecuta_nada(self):
        registro = RegistroStub({})
        ejecutor = EjecutorPlan(registro)

        resultado = ejecutor.ejecutar(_plan())

        self.assertEqual(resultado.resultados, ())
        self.assertTrue(resultado.exito)
        self.assertEqual(resultado.respuesta_compuesta, "")
        self.assertEqual(resultado.pasos_ejecutados(), [])
        self.assertEqual(resultado.pasos_fallidos(), [])
        self.assertEqual(registro.ejecutados, [])


class UnPasoExitosoTests(unittest.TestCase):
    def test_un_paso_exitoso(self):
        def _abrir(**kwargs):
            return ToolResult(exito=True, mensaje="Abriendo Chrome.", tool="tool_a")

        registro = _registro(_tool("tool_a", _abrir))
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(_paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        self.assertTrue(resultado.exito)
        self.assertEqual(len(resultado.resultados), 1)
        resultado_paso = resultado.resultados[0]
        self.assertEqual(resultado_paso.estado, ESTADO_EXITOSO)
        self.assertTrue(resultado_paso.ejecutado)
        self.assertTrue(resultado_paso.exito)
        self.assertEqual(resultado_paso.respuesta, "Abriendo Chrome.")
        self.assertEqual(resultado.respuesta_compuesta, "Abriendo Chrome.")
        self.assertEqual(len(resultado.pasos_ejecutados()), 1)
        self.assertEqual(resultado.pasos_fallidos(), [])


class DosPasosTests(unittest.TestCase):
    def _registro_orden(self):
        orden = []

        def _abrir(**kwargs):
            orden.append(("abrir", kwargs))
            return ToolResult(exito=True, mensaje="Abriendo Chrome.", tool="tool_a")

        def _buscar(**kwargs):
            orden.append(("buscar", kwargs))
            return ToolResult(exito=True, mensaje="Buscando gatos.", tool="tool_b")

        registro = _registro(_tool("tool_a", _abrir), _tool("tool_b", _buscar))
        return registro, orden

    def test_dos_pasos_exitosos_en_orden(self):
        registro, orden = self._registro_orden()
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"consulta": "gatos"}, valor="gatos"),
            )
        )

        self.assertTrue(resultado.exito)
        self.assertEqual(len(resultado.resultados), 2)
        estados = [r.estado for r in resultado.resultados]
        self.assertEqual(estados, [ESTADO_EXITOSO, ESTADO_EXITOSO])
        self.assertEqual(
            [nombre for nombre, _ in orden],
            ["abrir", "buscar"],
        )
        self.assertEqual(
            resultado.resultados[0].paso.tool,
            "tool_a",
        )
        self.assertEqual(resultado.resultados[1].paso.tool, "tool_b")

    def test_resultado_acumulado_conserva_el_orden(self):
        registro, _ = self._registro_orden()
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"consulta": "gatos"}, valor="gatos"),
            )
        )

        self.assertEqual(
            [r.paso.orden for r in resultado.resultados],
            [1, 2],
        )
        self.assertEqual(resultado.resultados[0].paso.parametros, {"aplicacion": "Chrome"})
        self.assertEqual(resultado.resultados[1].paso.parametros, {"consulta": "gatos"})

    def test_respuesta_compuesta_acumula_las_respuestas(self):
        registro, _ = self._registro_orden()
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"consulta": "gatos"}, valor="gatos"),
            )
        )

        self.assertEqual(
            resultado.respuesta_compuesta,
            "Abriendo Chrome.\nBuscando gatos.",
        )


class FalloYBloqueoTests(unittest.TestCase):
    def test_fallo_del_primer_paso_bloquea_los_siguientes(self):
        llamado = []

        def _falla(**kwargs):
            llamado.append("tool_a")
            return ToolResult(exito=False, mensaje="Fallo", tool="tool_a", error="Permiso denegado.")

        def _segunda(**kwargs):
            llamado.append("tool_b")
            return ToolResult(exito=True, mensaje="ok", tool="tool_b")

        registro = _registro(_tool("tool_a", _falla), _tool("tool_b", _segunda))
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"consulta": "gatos"}, valor="gatos"),
            )
        )

        self.assertFalse(resultado.exito)
        self.assertEqual(len(resultado.resultados), 2)
        primero, segundo = resultado.resultados
        self.assertEqual(primero.estado, ESTADO_FALLIDO)
        self.assertTrue(primero.ejecutado)
        self.assertFalse(primero.exito)
        self.assertIn("Permiso denegado.", primero.error)
        self.assertEqual(segundo.estado, ESTADO_BLOQUEADO)
        self.assertFalse(segundo.ejecutado)
        self.assertFalse(segundo.exito)
        self.assertEqual(llamado, ["tool_a"])
        self.assertEqual(len(resultado.pasos_fallidos()), 1)
        self.assertEqual(len(resultado.pasos_bloqueados()), 1)

    def test_fallo_del_segundo_paso_no_toca_al_primero(self):
        llamado = []

        def _abre(**kwargs):
            llamado.append("tool_a")
            return ToolResult(exito=True, mensaje="Abriendo.", tool="tool_a")

        def _falla(**kwargs):
            llamado.append("tool_b")
            return ToolResult(exito=False, mensaje="Fallo", tool="tool_b", error="Error navegador.")

        registro = _registro(_tool("tool_a", _abre), _tool("tool_b", _falla))
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"consulta": "gatos"}, valor="gatos"),
            )
        )

        self.assertFalse(resultado.exito)
        primero, segundo = resultado.resultados
        self.assertEqual(primero.estado, ESTADO_EXITOSO)
        self.assertEqual(segundo.estado, ESTADO_FALLIDO)
        self.assertIn("Error navegador.", segundo.error)
        self.assertEqual(llamado, ["tool_a", "tool_b"])

    def test_tres_pasos_primero_falla_y_todos_los_siguientes_se_bloquean(self):
        llamado = []

        def _falla(**kwargs):
            llamado.append("tool_a")
            return ToolResult(exito=False, mensaje="Fallo", tool="tool_a", error="Error.")

        def _exitoso(nombre):
            def _ejecutor(**kwargs):
                llamado.append(nombre)
                return ToolResult(exito=True, mensaje="ok", tool=nombre)

            return _ejecutor

        registro = _registro(
            _tool("tool_a", _falla),
            _tool("tool_b", _exitoso("tool_b")),
            _tool("tool_c", _exitoso("tool_c")),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"aplicacion": "Steam"}, valor="Steam"),
                _paso(3, "tool_c", {"consulta": "gatos"}, valor="gatos"),
            )
        )

        estados = [r.estado for r in resultado.resultados]
        self.assertEqual(estados, [ESTADO_FALLIDO, ESTADO_BLOQUEADO, ESTADO_BLOQUEADO])
        self.assertEqual(llamado, ["tool_a"])
        self.assertEqual(len(resultado.pasos_bloqueados()), 2)


class ToolInexistenteTests(unittest.TestCase):
    def test_tool_inexistente_no_ejecuta_nada_y_falla_con_error_claro(self):
        llamado = []

        def _exitoso(**kwargs):
            llamado.append("tool_a")
            return ToolResult(exito=True, mensaje="ok", tool="tool_a")

        registro = _registro(_tool("tool_a", _exitoso))
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(_paso(1, "tool_inexistente", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        self.assertFalse(resultado.exito)
        paso_resultado = resultado.resultados[0]
        self.assertEqual(paso_resultado.estado, ESTADO_FALLIDO)
        self.assertFalse(paso_resultado.ejecutado)
        self.assertIn("no esta registrada", paso_resultado.error)
        self.assertEqual(llamado, [])
        self.assertEqual(len(resultado.pasos_fallidos()), 1)

    def test_tool_inexistente_bloquea_los_pasos_siguientes(self):
        llamado = []

        def _exitoso(**kwargs):
            llamado.append("tool_b")
            return ToolResult(exito=True, mensaje="ok", tool="tool_b")

        registro = _registro(_tool("tool_b", _exitoso))
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_inexistente", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"aplicacion": "Steam"}, valor="Steam"),
            )
        )

        self.assertEqual(resultado.resultados[0].estado, ESTADO_FALLIDO)
        self.assertEqual(resultado.resultados[1].estado, ESTADO_BLOQUEADO)
        self.assertEqual(llamado, [])


class ParametrosInvalidosTests(unittest.TestCase):
    def test_parametro_requerido_faltante_no_ejecuta_la_tool(self):
        llamado = []

        def _abrir(**kwargs):
            llamado.append(kwargs)
            return ToolResult(exito=True, mensaje="ok", tool="tool_a")

        tool = _tool("tool_a", _abrir, parametros=(Parametro("aplicacion", requerido=True, tipo=str),))
        registro = _registro(tool)
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(_paso(1, "tool_a", {}, valor="Chrome"))
        )

        self.assertFalse(resultado.exito)
        paso_resultado = resultado.resultados[0]
        self.assertEqual(paso_resultado.estado, ESTADO_FALLIDO)
        self.assertIn("obligatorio", paso_resultado.error)
        self.assertEqual(llamado, [])

    def test_parametro_de_tipo_invalido_no_ejecuta_la_tool(self):
        llamado = []

        def _abrir(**kwargs):
            llamado.append(kwargs)
            return ToolResult(exito=True, mensaje="ok", tool="tool_a")

        tool = _tool("tool_a", _abrir, parametros=(Parametro("aplicacion", requerido=True, tipo=str),))
        registro = _registro(tool)
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(_paso(1, "tool_a", {"aplicacion": 123}, valor="Chrome"))
        )

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.resultados[0].estado, ESTADO_FALLIDO)
        self.assertIn("debe ser de tipo", resultado.resultados[0].error)
        self.assertEqual(llamado, [])


class OmitidoTests(unittest.TestCase):
    def test_paso_no_planificable_se_omite_y_continua(self):
        llamado = []

        def _exitoso(nombre):
            def _ejecutor(**kwargs):
                llamado.append(nombre)
                return ToolResult(exito=True, mensaje="ok", tool=nombre)

            return _ejecutor

        registro = _registro(
            _tool("tool_a", _exitoso("tool_a")),
            _tool("tool_b", _exitoso("tool_b")),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, None, estado=ESTADO_SIN_TOOL, valor="tareas"),
                _paso(3, "tool_b", {"aplicacion": "Steam"}, valor="Steam"),
            )
        )

        self.assertTrue(resultado.exito)
        estados = [r.estado for r in resultado.resultados]
        self.assertEqual(estados, [ESTADO_EXITOSO, ESTADO_OMITIDO, ESTADO_EXITOSO])
        omitido = resultado.resultados[1]
        self.assertFalse(omitido.ejecutado)
        self.assertFalse(omitido.exito)
        self.assertEqual(llamado, ["tool_a", "tool_b"])
        self.assertEqual(len(resultado.pasos_omitidos()), 1)


class ReutilizacionTests(unittest.TestCase):
    def test_reutiliza_toolregistry_para_localizar_y_ejecutar(self):
        recibido = []

        def _abrir(**kwargs):
            recibido.append(kwargs)
            return ToolResult(exito=True, mensaje="ok", tool="tool_a")

        registro = _registro(
            _tool(
                "tool_a",
                _abrir,
                parametros=(Parametro("aplicacion", requerido=True, tipo=str),),
            )
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(_paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        self.assertTrue(resultado.exito)
        self.assertEqual(recibido, [{"aplicacion": "Chrome"}])

    def test_no_ejecuta_herramientas_fuera_del_registry(self):
        def _abrir(**kwargs):
            return ToolResult(exito=True, mensaje="ok", tool="tool_a")

        stub = RegistroStub({"tool_a": _tool("tool_a", _abrir)})
        resultado = EjecutorPlan(stub).ejecutar(
            _plan(_paso(1, "tool_b", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.resultados[0].estado, ESTADO_FALLIDO)
        self.assertEqual(stub.ejecutados, [])


class EjecutorAccionesPCTests(unittest.TestCase):
    def test_abrir_aplicacion_pasa_por_ejecutoraccionespc(self):
        with mock.patch("core.tools.herramientas.aplicaciones.EjecutorAccionesPC") as ej_pc:
            instancia = ej_pc.return_value
            instancia.preparar.return_value = (
                ResultadoAccion(exito=True, mensaje="Abriendo Brave Browser.", accion="abrir_aplicacion"),
                None,
            )

            resultado = EjecutorPlan().ejecutar(
                _plan(_paso(1, "abrir_aplicacion", {"aplicacion": "Brave"}, valor="Brave"))
            )

        self.assertTrue(resultado.exito)
        paso_resultado = resultado.resultados[0]
        self.assertEqual(paso_resultado.estado, ESTADO_EXITOSO)
        self.assertIn("Abriendo Brave Browser.", paso_resultado.respuesta)
        ej_pc.assert_called_once()
        instancia.preparar.assert_called_once_with(
            "abrir_aplicacion",
            {"aplicacion": "Brave"},
        )


class NoModificaPlanTests(unittest.TestCase):
    def test_no_modifica_el_plan_original(self):
        def _abrir(**kwargs):
            return ToolResult(exito=True, mensaje="ok", tool="tool_a")

        paso = _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome")
        plan = _plan(paso)
        registro = _registro(_tool("tool_a", _abrir))

        resultado = EjecutorPlan(registro).ejecutar(plan)

        self.assertEqual(resultado.plan, plan)
        self.assertEqual(plan.pasos, (paso,))
        self.assertEqual(paso.tool, "tool_a")
        self.assertEqual(paso.parametros, {"aplicacion": "Chrome"})


class ResultadoPasoContratoTests(unittest.TestCase):
    def test_resultado_paso_es_contrato_congelado(self):
        paso = _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome")
        resultado_paso = ResultadoPaso(
            paso=paso,
            estado=ESTADO_EXITOSO,
            ejecutado=True,
            exito=True,
            respuesta="ok",
        )
        self.assertIsInstance(resultado_paso, ResultadoPaso)
        with self.assertRaises(AttributeError):
            resultado_paso.exito = False


if __name__ == "__main__":
    unittest.main()
