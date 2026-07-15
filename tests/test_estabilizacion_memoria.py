import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.conocimiento import normalizar_para_busqueda
from core.memoria import (
    construir_contexto_para_ia,
    inicializar_memoria,
    obtener_historial_conversacion,
    registrar_turno_conversacion,
)
from ia.prompts import construir_prompt_sistema
from ia.proveedor import RespuestaProveedor
from utilidades.rutas import configurar_base_datos


class EstabilizacionMemoriaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.config = {
            "modo": "normal",
            "ia": {
                "activada": True,
                "router": {"orden_proveedores": ["groq", "ollama"]},
                "limite_contexto": 900,
                "max_turnos": 3,
            },
        }

    def tearDown(self):
        configurar_base_datos(None)
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    def test_arena_breakout_queda_solo_en_videojuegos(self):
        memoria = inicializar_memoria({
            "usuario": {
                "gustos": {
                    "videojuegos": ["arena breakout"],
                    "otros": ["Arena Breakout"],
                }
            }
        })

        self.assertEqual(
            memoria["usuario"]["gustos"]["videojuegos"],
            ["Arena Breakout"],
        )
        self.assertNotIn(
            "Arena Breakout",
            memoria["usuario"]["gustos"]["otros"],
        )

    def test_duplicados_entre_categorias_desaparecen(self):
        memoria = inicializar_memoria({
            "usuario": {
                "gustos": {
                    "musica": ["rock"],
                    "otros": ["Rock", "dato unico"],
                }
            }
        })

        self.assertEqual(memoria["usuario"]["gustos"]["musica"], ["rock"])
        self.assertNotIn("Rock", memoria["usuario"]["gustos"]["otros"])
        self.assertIn("dato unico", memoria["usuario"]["gustos"]["otros"])

    def test_wosb_se_normaliza_y_migra_a_videojuegos(self):
        memoria = inicializar_memoria({
            "usuario": {"gustos": {"otros": ["wosb"]}}
        })

        self.assertIn(
            "World of Sea Battle",
            memoria["usuario"]["gustos"]["videojuegos"],
        )
        self.assertNotIn("wosb", memoria["usuario"]["gustos"]["otros"])

    def test_migracion_memoria_antigua_sube_version_y_conserva_unicos(self):
        memoria = inicializar_memoria({
            "sistema": {"version_memoria": 5},
            "usuario": {
                "gustos": {
                    "otros": ["objeto raro"],
                    "videojuegos": ["minecraft"],
                }
            },
        })

        self.assertEqual(memoria["sistema"]["version_memoria"], 6)
        self.assertIn("objeto raro", memoria["usuario"]["gustos"]["otros"])
        self.assertIn(
            "objeto raro",
            memoria["sistema"]["migracion_v6"]["conservados_otros"],
        )
        self.assertIn("Minecraft", memoria["usuario"]["gustos"]["videojuegos"])

    def test_historial_conversacional_recorta_turnos(self):
        memoria = inicializar_memoria({})

        for indice in range(5):
            registrar_turno_conversacion(
                memoria,
                f"mensaje {indice}",
                f"respuesta {indice}",
                limite=3,
            )

        self.assertEqual(len(memoria["conversacion"]), 3)
        self.assertEqual(memoria["conversacion"][0]["usuario"], "mensaje 2")
        self.assertEqual(len(obtener_historial_conversacion(memoria, 2)), 4)

    @mock.patch("core.cerebro.generar_respuesta")
    def test_aprendizaje_no_llama_a_ollama(self, generar):
        memoria = inicializar_memoria({})

        resultado = procesar("me gusta arena breakout", memoria, self.config)

        generar.assert_not_called()
        self.assertEqual(resultado.accion, "aprendizaje")
        self.assertIn("videojuegos", resultado.respuesta)

    def test_contexto_respeta_limite_e_incluye_conversacion(self):
        memoria = inicializar_memoria({})
        memoria["perfil"]["nombre"] = "michel"
        registrar_turno_conversacion(
            memoria,
            "hablemos de videojuegos",
            "Claro, hablemos de Factorio",
        )

        contexto = construir_contexto_para_ia(
            memoria,
            consulta="videojuegos",
            limite=90,
        )

        self.assertLessEqual(len(contexto), 90)
        self.assertIn("Consulta actual", contexto)

    def test_prompt_no_pide_razonamiento(self):
        prompt = construir_prompt_sistema("Perfil: nombre michel")
        normalizado = normalizar_para_busqueda(prompt)

        self.assertIn("orion", normalizado)
        self.assertIn("no muestres razonamiento interno", normalizado)
        self.assertIn("no inventes recuerdos", normalizado)

    @mock.patch("core.cerebro.generar_respuesta")
    def test_ollama_apagado_no_cierra_orion(self, generar):
        memoria = inicializar_memoria({})
        generar.return_value = RespuestaProveedor(
            "No pude usar IA en este momento.",
            "ninguno",
            error=True,
        )

        resultado = procesar("conversemos", memoria, self.config)

        self.assertEqual(resultado.accion, "error_ia")
        self.assertFalse(resultado.salir)
        self.assertEqual(memoria["conversacion"], [])

    @mock.patch("core.cerebro.generar_respuesta")
    def test_memoria_personal_no_cambia_en_conversacion_libre(self, generar):
        memoria = inicializar_memoria({})
        generar.return_value = RespuestaProveedor("Respuesta libre", "groq")
        antes = copy.deepcopy(memoria["usuario"])

        procesar("dime algo interesante", memoria, self.config)

        self.assertEqual(memoria["usuario"], antes)


if __name__ == "__main__":
    unittest.main()
