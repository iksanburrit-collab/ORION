import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import completar_solicitud, procesar
from core.memoria import (
    buscar_memoria,
    construir_contexto_para_ia,
    guardar_memoria,
    inicializar_memoria,
    listar_memorias_activas,
    listar_memorias_olvidadas,
    registrar_episodio,
)
from utilidades.archivos import cargar
from utilidades.rutas import configurar_base_datos, ruta_memoria


class MemoriasEstablesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"ia": {"activada": True}}

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def aprender(self, texto):
        return procesar(texto, self.memoria, self.config)

    def test_ids_y_estados_son_estables_tras_reinicio(self):
        self.aprender("me gusta minecraft")
        memoria_id = listar_memorias_activas(self.memoria)[0]["id"]
        guardar_memoria(self.memoria)

        recargada = inicializar_memoria(cargar(ruta_memoria(), {}))

        self.assertEqual(listar_memorias_activas(recargada)[0]["id"], memoria_id)
        self.assertEqual(listar_memorias_activas(recargada)[0]["estado"], "activa")

    def test_olvido_individual_no_afecta_contenido_igual_de_otro_tipo(self):
        registrar_episodio(
            self.memoria,
            "gusto",
            "Python",
            categoria="tecnologia",
        )
        registrar_episodio(
            self.memoria,
            "aprendizaje",
            "Python",
            categoria="lenguajes",
        )
        gusto, aprendizaje = listar_memorias_activas(self.memoria)

        solicitud = procesar(
            f"olvida memoria {gusto['id']}",
            self.memoria,
            self.config,
        ).solicitud_pendiente
        completar_solicitud(solicitud, "si", self.memoria, self.config)

        self.assertEqual(buscar_memoria(self.memoria, gusto["id"])["estado"], "olvidada")
        self.assertEqual(buscar_memoria(self.memoria, aprendizaje["id"])["estado"], "activa")
        self.assertEqual(len(listar_memorias_olvidadas(self.memoria)), 1)

    def test_eliminacion_cancelacion_y_persistencia(self):
        self.aprender("estoy aprendiendo python")
        memoria_id = listar_memorias_activas(self.memoria)[0]["id"]
        solicitud = procesar(
            f"borra memoria {memoria_id}",
            self.memoria,
            self.config,
        ).solicitud_pendiente

        cancelada = completar_solicitud(solicitud, "cancelar", self.memoria, self.config)
        self.assertEqual(cancelada.accion, "confirmacion_cancelada")
        self.assertEqual(buscar_memoria(self.memoria, memoria_id)["estado"], "activa")

        solicitud = procesar(
            f"elimina memoria {memoria_id}",
            self.memoria,
            self.config,
        ).solicitud_pendiente
        completar_solicitud(solicitud, "confirmar", self.memoria, self.config)
        recargada = inicializar_memoria(cargar(ruta_memoria(), {}))

        self.assertEqual(buscar_memoria(recargada, memoria_id)["estado"], "eliminada")
        self.assertEqual(listar_memorias_activas(recargada), [])
        self.assertEqual(listar_memorias_olvidadas(recargada), [])

    def test_contexto_incluye_solo_memoria_activa(self):
        self.aprender("me gusta minecraft")
        memoria_id = listar_memorias_activas(self.memoria)[0]["id"]
        solicitud = procesar(
            f"olvida memoria {memoria_id}",
            self.memoria,
            self.config,
        ).solicitud_pendiente
        completar_solicitud(solicitud, "si", self.memoria, self.config)

        contexto = construir_contexto_para_ia(self.memoria, consulta="videojuegos")
        normalizado = contexto.lower()
        self.assertNotIn("minecraft", normalizado)
        self.assertNotIn("olvido", normalizado)

    def test_listados_muestran_id_y_estado_correcto(self):
        self.aprender("me gusta factorio")
        memoria_id = listar_memorias_activas(self.memoria)[0]["id"]
        activo = procesar("mis memorias", self.memoria, self.config)
        solicitud = procesar(
            f"olvida memoria {memoria_id}", self.memoria, self.config
        ).solicitud_pendiente
        completar_solicitud(solicitud, "si", self.memoria, self.config)
        normal = procesar("mis memorias", self.memoria, self.config)
        olvidadas = procesar("memorias olvidadas", self.memoria, self.config)

        self.assertIn(memoria_id, activo.respuesta)
        self.assertNotIn("Factorio", normal.respuesta)
        self.assertIn(memoria_id, olvidadas.respuesta)

    def test_compatibilidad_legacy_asigna_id_y_olvida_registro_concreto(self):
        antigua = {
            "episodica": {
                "eventos": [
                    {
                        "tipo": "gusto",
                        "contenido": "Minecraft",
                        "categoria": "videojuegos",
                        "fecha": "2026-01-01T00:00:00+00:00",
                    },
                    {
                        "tipo": "olvido",
                        "contenido": "Minecraft",
                        "categoria": "videojuegos",
                        "fecha": "2026-01-02T00:00:00+00:00",
                    },
                ]
            }
        }

        migrada = inicializar_memoria(antigua)

        self.assertEqual(len(listar_memorias_olvidadas(migrada)), 1)
        self.assertTrue(listar_memorias_olvidadas(migrada)[0]["id"].startswith("mem-"))

    @mock.patch("core.cerebro.generar_respuesta")
    def test_comando_invalido_o_id_inexistente_no_llega_a_ia(self, generar):
        invalido = procesar("borra memoria", self.memoria, self.config)
        inexistente = procesar("borra memoria 1", self.memoria, self.config)

        self.assertEqual(invalido.accion, "ayuda_comando_local")
        self.assertEqual(inexistente.accion, "memoria_no_encontrada")
        generar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
