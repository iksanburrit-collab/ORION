import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.handlers.contratos import ResultadoCerebro, _paso_como_dict
from core.interprete import TIPO_APLICACION, Entidad
from core.planificador import ESTADO_PLANIFICABLE, Paso


def _paso(orden, verbo, entidad_valor, tool):
    return Paso(
        orden=orden,
        verbo=verbo,
        entidad=Entidad(
            tipo=TIPO_APLICACION,
            valor=entidad_valor,
            normalizado=entidad_valor.lower(),
        ),
        tool=tool,
        parametros={},
        estado=ESTADO_PLANIFICABLE,
        motivo="Operacion planificada.",
        texto=f"{verbo} {entidad_valor}",
    )


class ResultadoCerebroCeroAccionesTests(unittest.TestCase):
    def test_por_defecto_sin_acciones(self):
        resultado = ResultadoCerebro(texto="hola", intencion="saludo")

        self.assertEqual(resultado.acciones, ())
        self.assertEqual(resultado.respuestas, ())
        self.assertFalse(resultado.reconocido)
        self.assertEqual(resultado.accion, "")
        self.assertEqual(resultado.respuesta, "")

    def test_respuesta_compuesta_vacia(self):
        resultado = ResultadoCerebro(texto="hola", intencion="saludo")
        self.assertEqual(resultado.respuesta_compuesta(), "")


class ResultadoCerebroUnaAccionTests(unittest.TestCase):
    def test_una_accion(self):
        paso = _paso(0, "abrir", "Steam", "abrir_aplicacion")
        resultado = ResultadoCerebro(
            texto="abre Steam",
            intencion="aplicaciones",
            acciones=(paso,),
        )

        self.assertEqual(len(resultado.acciones), 1)
        self.assertIs(resultado.acciones[0], paso)

    def test_accion_individual_con_respuesta(self):
        resultado = ResultadoCerebro(texto="abre Steam", intencion="aplicaciones")
        resultado.agregar_accion(
            _paso(0, "abrir", "Steam", "abrir_aplicacion"),
            respuesta="Abriendo Steam",
        )

        self.assertEqual(resultado.acciones[0].verbo, "abrir")
        self.assertEqual(resultado.respuestas, ("Abriendo Steam",))
        self.assertEqual(resultado.respuesta_compuesta(), "Abriendo Steam")


class ResultadoCerebroMultiplesAccionesTests(unittest.TestCase):
    def test_multiples_acciones_ordenadas(self):
        pasos = (
            _paso(0, "abrir", "Chrome", "abrir_aplicacion"),
            _paso(1, "buscar", "gatos", "abrir_navegador"),
        )
        resultado = ResultadoCerebro(
            texto="abre Chrome y busca gatos",
            intencion="acciones",
            acciones=pasos,
        )

        self.assertEqual(len(resultado.acciones), 2)
        self.assertEqual(
            [paso.verbo for paso in resultado.acciones],
            ["abrir", "buscar"],
        )

    def test_orden_se_conserva_al_agregar(self):
        resultado = ResultadoCerebro(texto="varias acciones", intencion="acciones")
        for orden, verbo, valor, tool in (
            (0, "abrir", "Chrome", "abrir_aplicacion"),
            (1, "abrir", "Edge", "abrir_aplicacion"),
            (2, "buscar", "gatos", "abrir_navegador"),
        ):
            resultado.agregar_accion(_paso(orden, verbo, valor, tool))

        self.assertEqual(
            [paso.orden for paso in resultado.acciones],
            [0, 1, 2],
        )
        self.assertEqual(resultado.acciones[0].entidad.valor, "Chrome")
        self.assertEqual(resultado.acciones[2].entidad.valor, "gatos")


class ResultadoCerebroCompatibilidadTests(unittest.TestCase):
    def test_accion_sigue_siendo_cadena(self):
        resultado = ResultadoCerebro(
            texto="salir",
            intencion="salir",
            accion="salir",
        )
        self.assertEqual(resultado.accion, "salir")
        self.assertIsInstance(resultado.accion, str)

    def test_accion_se_puede_reescribir(self):
        resultado = ResultadoCerebro(texto="x", intencion="y")
        resultado.accion = "navegador"
        self.assertEqual(resultado.accion, "navegador")

    def test_respuesta_compatible(self):
        resultado = ResultadoCerebro(
            texto="hola",
            intencion="saludo",
            respuesta="Hola 👋",
        )
        self.assertEqual(resultado.respuesta, "Hola 👋")

    def test_solicitud_de_texto(self):
        resultado = ResultadoCerebro(
            texto="nombre",
            intencion="nombre",
            solicitud="nombre",
        )
        self.assertEqual(resultado.solicitud, "nombre")

    def test_solicitud_estructurada(self):
        solicitud = {"tipo": "confirmar_tarea", "accion": "eliminar_tarea"}
        resultado = ResultadoCerebro(
            texto="si",
            intencion="confirmar_tarea",
            solicitud=solicitud,
        )
        self.assertEqual(resultado.solicitud, solicitud)

    def test_solicitud_pendiente_compatible(self):
        pendiente = {"tipo": "confirmar_memoria"}
        resultado = ResultadoCerebro(
            texto="si",
            intencion="confirmar_memoria",
            solicitud_pendiente=pendiente,
        )
        self.assertEqual(resultado.solicitud_pendiente, pendiente)

    def test_salir_y_conocimiento_y_debug(self):
        resultado = ResultadoCerebro(
            texto="salir",
            intencion="salir",
            salir=True,
            conocimiento={"tipo": "gusto"},
            debug={"tiempo_respuesta": 0.1},
        )
        self.assertTrue(resultado.salir)
        self.assertEqual(resultado.conocimiento, {"tipo": "gusto"})
        self.assertEqual(resultado.debug, {"tiempo_respuesta": 0.1})


class ResultadoCerebroConstructorCompatibilidadTests(unittest.TestCase):
    def test_constructor_posicional_antiguo(self):
        resultado = ResultadoCerebro(
            "abre Chrome",
            "aplicaciones",
            "abrir_aplicacion",
            "Abriendo Chrome",
        )
        self.assertEqual(resultado.texto, "abre Chrome")
        self.assertEqual(resultado.intencion, "aplicaciones")
        self.assertEqual(resultado.accion, "abrir_aplicacion")
        self.assertEqual(resultado.respuesta, "Abriendo Chrome")
        self.assertEqual(resultado.acciones, ())

    def test_constructor_por_palabras_clave_como_cerebro(self):
        resultado = ResultadoCerebro(
            texto="valor",
            intencion="solicitud_desconocida",
            accion="solicitud_desconocida",
            respuesta="No pude completar esa solicitud.",
        )
        self.assertEqual(resultado.accion, "solicitud_desconocida")


class ResultadoCerebroSerializacionTests(unittest.TestCase):
    def test_como_dict_incluye_acciones(self):
        paso = _paso(0, "abrir", "Steam", "abrir_aplicacion")
        resultado = ResultadoCerebro(
            texto="abre Steam",
            intencion="aplicaciones",
            acciones=(paso,),
        )

        datos = resultado.como_dict()
        self.assertEqual(datos["acciones"][0]["verbo"], "abrir")
        self.assertEqual(datos["acciones"][0]["tool"], "abrir_aplicacion")
        self.assertEqual(
            datos["acciones"][0]["entidad"],
            {"tipo": TIPO_APLICACION, "valor": "Steam", "normalizado": "steam"},
        )
        self.assertEqual(datos["respuestas"], ())
        self.assertFalse(datos["reconocido"])

    def test_paso_sin_entidad_se_serializa_con_none(self):
        paso = Paso(
            orden=0,
            verbo="abrir",
            entidad=None,
            tool=None,
            parametros={},
            estado="sin_tool",
            motivo="No existe ninguna Tool.",
            texto="abre",
        )
        datos = _paso_como_dict(paso)
        self.assertIsNone(datos["entidad"])
        self.assertIsNone(datos["tool"])
        self.assertEqual(datos["estado"], "sin_tool")

    def test_repr_del_resultado(self):
        resultado = ResultadoCerebro(
            texto="hola",
            intencion="saludo",
            accion="saludar",
        )
        self.assertIn("ResultadoCerebro", repr(resultado))
        self.assertIn("acciones=()", repr(resultado))


class ResultadoCerebroRespuestaCompuestaTests(unittest.TestCase):
    def test_respuesta_compuesta_con_una_respuesta(self):
        resultado = ResultadoCerebro(texto="x", intencion="y")
        resultado.agregar_accion(
            _paso(0, "abrir", "Chrome", "abrir_aplicacion"),
            respuesta="Abriendo Chrome",
        )
        self.assertEqual(resultado.respuesta_compuesta(), "Abriendo Chrome")

    def test_respuesta_compuesta_multi_respuestas(self):
        resultado = ResultadoCerebro(texto="x", intencion="y")
        resultado.agregar_accion(
            _paso(0, "abrir", "Chrome", "abrir_aplicacion"),
            respuesta="Abriendo Chrome",
        )
        resultado.agregar_accion(
            _paso(1, "buscar", "gatos", "abrir_navegador"),
            respuesta="Abriendo navegador",
        )

        self.assertEqual(
            resultado.respuesta_compuesta(),
            "Abriendo Chrome\nAbriendo navegador",
        )

    def test_respuesta_compuesta_con_separador_personalizado(self):
        resultado = ResultadoCerebro(texto="x", intencion="y")
        resultado.agregar_accion(
            _paso(0, "abrir", "Chrome", "abrir_aplicacion"),
            respuesta="Abriendo Chrome",
        )
        resultado.agregar_accion(
            _paso(1, "buscar", "gatos", "abrir_navegador"),
            respuesta="Abriendo navegador",
        )

        self.assertEqual(
            resultado.respuesta_compuesta(separador=" | "),
            "Abriendo Chrome | Abriendo navegador",
        )

    def test_respuesta_compuesta_falla_a_la_respuesta_unica(self):
        resultado = ResultadoCerebro(
            texto="hola",
            intencion="saludo",
            respuesta="Hola 👋",
        )
        self.assertEqual(resultado.respuesta_compuesta(), "Hola 👋")

    def test_agregar_accion_sin_respuesta_no_anade_a_respuestas(self):
        resultado = ResultadoCerebro(texto="x", intencion="y")
        resultado.agregar_accion(_paso(0, "abrir", "Chrome", "abrir_aplicacion"))

        self.assertEqual(resultado.acciones, (_paso(0, "abrir", "Chrome", "abrir_aplicacion"),))
        self.assertEqual(resultado.respuestas, ())
        self.assertEqual(resultado.respuesta_compuesta(), "")


class ResultadoCerebroComportamientoAntiguoTests(unittest.TestCase):
    def test_procesar_sigue_devolviendo_accion_y_respuesta(self):
        from core.cerebro import procesar

        resultado = procesar("salir", {}, {"ia": {"activada": False}})
        self.assertEqual(resultado.accion, "salir")
        self.assertTrue(resultado.salir)
        self.assertEqual(resultado.acciones, ())


if __name__ == "__main__":
    unittest.main()