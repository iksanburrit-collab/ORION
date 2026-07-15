import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import completar_solicitud, procesar
from core.memoria import inicializar_memoria
from servicios.notas import RepositorioNotas
from utilidades.rutas import configurar_base_datos, ruta_notas


class NotasEstablesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {"ia": {"activada": True}}
        self.repositorio = RepositorioNotas()
        self.notas = self.repositorio.datos

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def ejecutar(self, texto):
        return procesar(
            texto,
            self.memoria,
            self.config,
            notas=self.notas,
            guardar_notas=self.repositorio.guardar,
            archivo_notas=self.repositorio.archivo,
        )

    @mock.patch("core.cerebro.generar_respuesta")
    def test_creacion_y_listado_local_con_ids(self, generar):
        creada = self.ejecutar("anota revisar backups")
        legacy = self.ejecutar("recuerda comprar pilas")
        listado = self.ejecutar("mis notas")

        self.assertEqual(creada.accion, "guardar_nota")
        self.assertEqual(legacy.accion, "guardar_nota")
        self.assertIn("nota-1", listado.respuesta)
        self.assertIn("nota-2", listado.respuesta)
        generar.assert_not_called()

    def test_migracion_legacy_persiste_ids_estables(self):
        Path(ruta_notas()).write_text(
            json.dumps(["nota antigua", "otra nota"]),
            encoding="utf-8",
        )

        primera = RepositorioNotas()
        ids_primera = [nota.id for nota in primera.listar_activas()]
        segunda = RepositorioNotas()

        self.assertEqual(ids_primera, ["nota-1", "nota-2"])
        self.assertEqual(
            ids_primera,
            [nota.id for nota in segunda.listar_activas()],
        )

    def test_eliminacion_individual_cancelacion_y_persistencia(self):
        self.ejecutar("anota conservar esto")
        solicitud = self.ejecutar("borra nota nota-1").solicitud_pendiente

        cancelada = completar_solicitud(solicitud, "no", self.memoria, self.config)
        self.assertEqual(cancelada.accion, "confirmacion_cancelada")
        self.assertEqual(len(RepositorioNotas().listar_activas()), 1)

        solicitud = self.ejecutar("elimina nota nota-1").solicitud_pendiente
        confirmada = completar_solicitud(
            solicitud,
            "confirmar",
            self.memoria,
            self.config,
        )

        self.assertEqual(confirmada.accion, "eliminar_nota")
        self.assertEqual(RepositorioNotas().listar_activas(), [])
        self.assertEqual(RepositorioNotas().datos[0]["estado"], "eliminada")

    def test_eliminacion_total_requiere_confirmacion(self):
        self.ejecutar("anota uno")
        self.ejecutar("anota dos")
        solicitud = self.ejecutar("borrar notas").solicitud_pendiente

        self.assertEqual(solicitud["identificador"], "todas")
        self.assertEqual(solicitud["accion"], "eliminar_todas_notas")
        completar_solicitud(solicitud, "si", self.memoria, self.config)
        self.assertEqual(RepositorioNotas().listar_activas(), [])

    @mock.patch("core.cerebro.generar_respuesta")
    def test_id_inexistente_no_llega_a_ia(self, generar):
        resultado = self.ejecutar("elimina nota 1")

        self.assertEqual(resultado.accion, "nota_no_encontrada")
        self.assertIn("mis notas", resultado.respuesta)
        generar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
