import os
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import completar_solicitud
from core.handlers.tareas import procesar_tareas
from servicios.calendario.local import ProveedorCalendarioLocal


class TareasCalendarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.archivo = os.path.join(self.tmp.name, "calendario.json")
        self.proveedor = ProveedorCalendarioLocal(self.archivo)
        self.config = {"ia": {"activada": False}}
        self.memoria = {}

    def tearDown(self):
        self.tmp.cleanup()

    def procesar(self, texto):
        return procesar_tareas(texto, proveedor=self.proveedor)

    def test_crear_listar_completar(self):
        creado = self.procesar("agrega tarea terminar documentacion")
        listado = self.procesar("mis tareas")

        self.assertEqual(creado[1], "agregar_tarea")
        self.assertIn("local-1", listado[2])

        completado = self.procesar("completa tarea local-1")
        pendientes = self.procesar("tareas pendientes")

        self.assertEqual(completado[1], "completar_tarea")
        self.assertIn("No hay tareas", pendientes[2])

    def test_eliminar_con_confirmacion(self):
        self.procesar("nueva tarea limpiar backlog")
        solicitud = self.procesar("elimina tarea local-1")[3]

        self.assertEqual(solicitud["identificador"], "local-1")
        self.assertEqual(solicitud["accion"], "eliminar_tarea")
        self.assertIn("archivo", solicitud["datos"])

        respuesta = completar_solicitud(
            solicitud,
            "confirmar",
            self.memoria,
            self.config,
        )

        self.assertEqual(respuesta.accion, "eliminar_tarea")
        recargado = ProveedorCalendarioLocal(self.archivo)
        self.assertEqual(recargado.listar_eventos(), [])

    def test_confirmacion_alterada_no_elimina_otra_tarea(self):
        self.procesar("nueva tarea conservar")
        solicitud = self.procesar("elimina tarea local-1")[3]
        solicitud["identificador"] = "local-2"

        respuesta = completar_solicitud(
            solicitud,
            "si",
            self.memoria,
            self.config,
        )

        self.assertIn("No pude", respuesta.respuesta)
        self.assertEqual(len(self.proveedor.listar_eventos()), 1)

    def test_ids_eliminados_no_se_reutilizan(self):
        self.procesar("nueva tarea primera")
        solicitud = self.procesar("elimina tarea local-1")[3]
        completar_solicitud(solicitud, "si", self.memoria, self.config)

        nueva = self.procesar("nueva tarea segunda")

        self.assertIn("local-2", nueva[2])

    def test_ids_unicos_y_persistencia(self):
        self.procesar("agrega tarea uno")
        self.procesar("agrega tarea dos")

        recargado = ProveedorCalendarioLocal(self.archivo)
        ids = [evento.id for evento in recargado.listar_eventos()]

        self.assertEqual(ids, ["local-1", "local-2"])

    def test_migracion_formato_antiguo(self):
        with open(self.archivo, "w", encoding="utf-8") as archivo:
            archivo.write('["tarea vieja"]')

        migrado = ProveedorCalendarioLocal(self.archivo)

        self.assertEqual(migrado.listar_eventos()[0].titulo, "tarea vieja")
        self.assertEqual(migrado.listar_eventos()[0].id, "local-1")

    def test_no_toca_recordatorios_real(self):
        self.procesar("agrega tarea aislada")

        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "recordatorios.json")))


if __name__ == "__main__":
    unittest.main()
