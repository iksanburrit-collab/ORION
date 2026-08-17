import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.ejecutor import (
    ESTADO_BLOQUEADO,
    ESTADO_EXITOSO,
    ESTADO_FALLIDO,
    ESTADO_OMITIDO,
    ESTADO_REQUIERE_CONFIRMACION,
    EjecutorPlan,
)
from core.interprete.contratos import Entidad
from core.planificador.contratos import (
    ESTADO_PLANIFICABLE,
    ESTADO_SIN_TOOL,
    Paso,
    Plan,
)
from core.tools.contratos import (
    POLITICA_AUTO,
    POLITICA_BLOQUEAR,
    POLITICA_CONFIRMAR,
    Parametro,
    Tool,
    ToolResult,
)
from core.tools.registro import ToolRegistry


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
        verbo="abrir",
        entidad=entidad,
        tool=tool,
        parametros=parametros or {},
        estado=estado,
        motivo="Planificado." if estado == ESTADO_PLANIFICABLE else "Paso no ejecutable.",
        texto=f"{valor or 'operacion'} #{orden}",
    )


def _plan(*pasos: Paso) -> Plan:
    return Plan(texto_original="", pasos=pasos, reconocido=True, resoluble=True)


def _tool(nombre: str, politica: str, ejecutor=None) -> Tool:
    return Tool(
        name=nombre,
        description=f"Tool {nombre}.",
        ejecutor=ejecutor or (lambda **kwargs: ToolResult(True, "ok", nombre)),
        politica=politica,
    )


def _registro(*tools: Tool) -> ToolRegistry:
    registro = ToolRegistry()
    for tool in tools:
        registro.registrar(tool)
    return registro


class PoliticaAUTOTests(unittest.TestCase):
    def test_auto_se_ejecuta_directamente_sin_confirmacion(self):
        llamado = []

        def _abrir(**kwargs):
            llamado.append(kwargs)
            return ToolResult(True, "Abriendo Chrome.", "tool_a")

        tool = Tool(
            name="tool_a",
            description="Tool de prueba.",
            ejecutor=_abrir,
            politica=POLITICA_AUTO,
        )
        resultado = EjecutorPlan(_registro(tool)).ejecutar(
            _plan(_paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        self.assertTrue(resultado.exito)
        self.assertFalse(resultado.requiere_confirmacion)
        self.assertIsNone(resultado.solicitud)
        self.assertEqual(resultado.resultados[0].estado, ESTADO_EXITOSO)
        self.assertEqual(len(llamado), 1)
        self.assertEqual(resultado.resultados[0].respuesta, "Abriendo Chrome.")


class PoliticaCONFIRMARTests(unittest.TestCase):
    def test_confirmar_no_ejecuta_y_pide_autorizacion(self):
        llamado = []

        def _abrir(**kwargs):
            llamado.append(kwargs)
            return ToolResult(True, "Abriendo.", "tool_a")

        tool = _tool("tool_a", POLITICA_CONFIRMAR, _abrir)
        resultado = EjecutorPlan(_registro(tool)).ejecutar(
            _plan(_paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        self.assertTrue(resultado.requiere_confirmacion)
        self.assertEqual(llamado, [])
        self.assertEqual(len(resultado.resultados), 1)
        paso_resultado = resultado.resultados[0]
        self.assertEqual(paso_resultado.estado, ESTADO_REQUIERE_CONFIRMACION)
        self.assertFalse(paso_resultado.ejecutado)
        self.assertFalse(paso_resultado.exito)

    def test_solicitud_estructurada_identifica_paso_tool_y_motivo(self):
        tool = _tool("tool_a", POLITICA_CONFIRMAR)
        resultado = EjecutorPlan(_registro(tool)).ejecutar(
            _plan(_paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        solicitud = resultado.solicitud
        self.assertIsNotNone(solicitud)
        self.assertEqual(solicitud["tipo"], "confirmar_politica")
        self.assertEqual(solicitud["tool"], "tool_a")
        self.assertEqual(solicitud["paso"], 1)
        self.assertEqual(solicitud["accion"], "tool_a")
        self.assertIn("autorizacion", solicitud["motivo"])
        self.assertIn("autorizacion", solicitud["texto_confirmacion"])
        self.assertEqual(solicitud["parametros"], {"aplicacion": "Chrome"})

    def test_la_solicitud_no_se_trata_como_fallo(self):
        tool = _tool("tool_a", POLITICA_CONFIRMAR)
        resultado = EjecutorPlan(_registro(tool)).ejecutar(
            _plan(_paso(1, "tool_a", {}, valor="Chrome"))
        )

        self.assertNotEqual(resultado.resultados[0].estado, ESTADO_FALLIDO)
        self.assertTrue(resultado.exito)
        self.assertEqual(resultado.pasos_fallidos(), [])


class PoliticaBLOQUEARTests(unittest.TestCase):
    def test_bloquear_no_ejecuta_y_explica_motivo(self):
        llamado = []

        def _abrir(**kwargs):
            llamado.append(kwargs)
            return ToolResult(True, "Abriendo.", "tool_a")

        tool = _tool("tool_a", POLITICA_BLOQUEAR, _abrir)
        resultado = EjecutorPlan(_registro(tool)).ejecutar(
            _plan(_paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        self.assertEqual(llamado, [])
        paso_resultado = resultado.resultados[0]
        self.assertEqual(paso_resultado.estado, ESTADO_BLOQUEADO)
        self.assertFalse(paso_resultado.ejecutado)
        self.assertFalse(paso_resultado.exito)
        self.assertIn("bloqueada por politica", paso_resultado.error)
        self.assertEqual(len(resultado.pasos_bloqueados()), 1)


class PlanesMultiPasoTests(unittest.TestCase):
    def _exitoso(self, nombre):
        def _ejecutor(**kwargs):
            return ToolResult(True, f"ok {nombre}", nombre)

        return _ejecutor

    def test_auto_mas_auto_ejecuta_ambos(self):
        registro = _registro(
            _tool("tool_a", POLITICA_AUTO, self._exitoso("tool_a")),
            _tool("tool_b", POLITICA_AUTO, self._exitoso("tool_b")),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"aplicacion": "Steam"}, valor="Steam"),
            )
        )

        self.assertTrue(resultado.exito)
        self.assertFalse(resultado.requiere_confirmacion)
        estados = [r.estado for r in resultado.resultados]
        self.assertEqual(estados, [ESTADO_EXITOSO, ESTADO_EXITOSO])
        self.assertEqual(
            resultado.respuesta_compuesta,
            "ok tool_a\nok tool_b",
        )

    def test_auto_mas_confirmar_ejecuta_primero_y_pausa_en_segundo(self):
        llamado = []

        def _segunda(**kwargs):
            llamado.append("tool_b")
            return ToolResult(True, "ok tool_b", "tool_b")

        registro = _registro(
            _tool("tool_a", POLITICA_AUTO, self._exitoso("tool_a")),
            _tool("tool_b", POLITICA_CONFIRMAR, _segunda),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"aplicacion": "Steam"}, valor="Steam"),
            )
        )

        self.assertTrue(resultado.requiere_confirmacion)
        estados = [r.estado for r in resultado.resultados]
        self.assertEqual(estados, [ESTADO_EXITOSO, ESTADO_REQUIERE_CONFIRMACION])
        self.assertEqual(llamado, [])
        self.assertEqual(resultado.paso_pendiente.paso.orden, 2)
        self.assertEqual(resultado.paso_pendiente.estado, ESTADO_REQUIERE_CONFIRMACION)
        self.assertEqual(resultado.pasos_con_confirmacion(), [resultado.paso_pendiente])

    def test_auto_mas_confirmar_mas_auto_el_tercero_no_se_ejecuta(self):
        llamado = []

        def _tercera(**kwargs):
            llamado.append("tool_c")
            return ToolResult(True, "ok tool_c", "tool_c")

        registro = _registro(
            _tool("tool_a", POLITICA_AUTO, self._exitoso("tool_a")),
            _tool("tool_b", POLITICA_CONFIRMAR),
            _tool("tool_c", POLITICA_AUTO, _tercera),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"aplicacion": "Steam"}, valor="Steam"),
                _paso(3, "tool_c", {"consulta": "gatos"}, valor="gatos"),
            )
        )

        self.assertTrue(resultado.requiere_confirmacion)
        estados = [r.estado for r in resultado.resultados]
        self.assertEqual(estados, [ESTADO_EXITOSO, ESTADO_REQUIERE_CONFIRMACION])
        self.assertEqual(len(resultado.resultados), 2)
        self.assertEqual(llamado, [])
        self.assertEqual(resultado.paso_pendiente.paso.orden, 2)

    def test_conserva_los_resultados_anteriores_al_paso_pendiente(self):
        registro = _registro(
            _tool("tool_a", POLITICA_AUTO, self._exitoso("tool_a")),
            _tool("tool_b", POLITICA_CONFIRMAR),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"aplicacion": "Steam"}, valor="Steam"),
            )
        )

        previos = resultado.resultados_previos()
        self.assertEqual(len(previos), 1)
        self.assertEqual(previos[0].paso.orden, 1)
        self.assertEqual(previos[0].estado, ESTADO_EXITOSO)
        self.assertEqual(resultado.resultados[0].respuesta, "ok tool_a")
        self.assertEqual(len(resultado.pasos_ejecutados()), 1)

    def test_no_vuelve_a_ejecutar_el_primer_paso_en_resultado_pendiente(self):
        registro = _registro(
            _tool("tool_a", POLITICA_AUTO, self._exitoso("tool_a")),
            _tool("tool_b", POLITICA_CONFIRMAR),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"),
                _paso(2, "tool_b", {"aplicacion": "Steam"}, valor="Steam"),
            )
        )

        self.assertEqual(len(resultado.resultados_previos()), 1)
        self.assertEqual(resultado.paso_pendiente.paso.orden, 2)


class ConfirmacionNoEsFalloTests(unittest.TestCase):
    def test_requiere_confirmacion_no_es_fallo_ni_bloqueo(self):
        registro = _registro(
            _tool("tool_a", POLITICA_AUTO),
            _tool("tool_b", POLITICA_CONFIRMAR),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {}, valor="Chrome"),
                _paso(2, "tool_b", {}, valor="Steam"),
            )
        )

        self.assertTrue(resultado.exito)
        self.assertEqual(resultado.pasos_fallidos(), [])
        self.assertEqual(resultado.pasos_bloqueados(), [])
        self.assertEqual(len(resultado.pasos_con_confirmacion()), 1)
        self.assertEqual(resultado.paso_pendiente.estado, ESTADO_REQUIERE_CONFIRMACION)

    def test_bloqueado_si_se_detiene_por_politica(self):
        registro = _registro(
            _tool("tool_a", POLITICA_BLOQUEAR),
            _tool("tool_b", POLITICA_AUTO),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {}, valor="Chrome"),
                _paso(2, "tool_b", {}, valor="Steam"),
            )
        )

        estados = [r.estado for r in resultado.resultados]
        self.assertEqual(estados, [ESTADO_BLOQUEADO, ESTADO_BLOQUEADO])
        self.assertEqual(len(resultado.pasos_bloqueados()), 2)


class ToolRegistryUnicaViaTests(unittest.TestCase):
    def test_la_confirmacion_no_ejecuta_la_tool_fuera_del_registry(self):
        llamado = []

        def _abrir(**kwargs):
            llamado.append(kwargs)
            return ToolResult(True, "ok", "tool_a")

        tool = Tool(
            name="tool_a",
            description="Tool de prueba.",
            ejecutor=_abrir,
            politica=POLITICA_CONFIRMAR,
        )
        registro = ToolRegistry()
        registro.registrar(tool)
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(_paso(1, "tool_a", {"aplicacion": "Chrome"}, valor="Chrome"))
        )

        self.assertEqual(llamado, [])
        self.assertTrue(resultado.requiere_confirmacion)
        self.assertEqual(resultado.resultados[0].estado, ESTADO_REQUIERE_CONFIRMACION)

    def test_omitido_y_auto_continuan_normal(self):
        registro = _registro(
            _tool("tool_a", POLITICA_AUTO),
        )
        resultado = EjecutorPlan(registro).ejecutar(
            _plan(
                _paso(1, "tool_a", {}, valor="Chrome"),
                _paso(2, None, estado=ESTADO_SIN_TOOL, valor="tareas"),
            )
        )

        estados = [r.estado for r in resultado.resultados]
        self.assertEqual(estados, [ESTADO_EXITOSO, ESTADO_OMITIDO])
        self.assertTrue(resultado.exito)


class IntegracionCerebroTests(unittest.TestCase):
    def test_procesar_expone_la_solicitud_cuando_una_tool_requiere_confirmacion(self):
        import core.cerebro as cerebro

        llamado = []

        def _abrir_confirmado(**kwargs):
            llamado.append(kwargs)
            return ToolResult(True, "Abriendo.", "abrir_aplicacion")

        tool = Tool(
            name="abrir_aplicacion",
            description="Abre una aplicacion (requiere autorizacion).",
            ejecutor=_abrir_confirmado,
            parametros=(
                Parametro("aplicacion", requerido=True, tipo=str, descripcion="Aplicacion."),
                Parametro("config", requerido=False, tipo=dict, descripcion="Configuracion."),
            ),
            politica=POLITICA_CONFIRMAR,
        )
        registro = ToolRegistry()
        registro._asegurar_base()
        registro._tools["abrir_aplicacion"] = tool

        ejecutor_original = cerebro._EJECUTOR_PLAN
        try:
            cerebro._EJECUTOR_PLAN = EjecutorPlan(registro)
            resultado = cerebro.procesar(
                "abre steam",
                memoria={},
                config={},
            )
        finally:
            cerebro._EJECUTOR_PLAN = ejecutor_original

        self.assertEqual(llamado, [])
        self.assertEqual(resultado.accion, "ejecutar_plan")
        self.assertTrue(resultado.reconocido)
        self.assertIsNotNone(resultado.solicitud)
        self.assertEqual(resultado.solicitud["tipo"], "confirmar_politica")
        self.assertEqual(resultado.solicitud["tool"], "abrir_aplicacion")
        self.assertEqual(resultado.solicitud["paso"], 0)
        self.assertIsNotNone(resultado.solicitud_pendiente)
        self.assertEqual(resultado.solicitud_pendiente, resultado.solicitud)
        self.assertIn("autorizacion", resultado.respuesta)
        self.assertTrue(resultado.debug["ejecucion"]["requiere_confirmacion"])
        self.assertEqual(resultado.debug["ejecucion"]["paso_pendiente"], 0)


if __name__ == "__main__":
    unittest.main()