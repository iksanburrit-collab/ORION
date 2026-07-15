import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.memoria import inicializar_memoria
from servicios.calendario.legacy import migrar_recordatorios_legacy
from servicios.calendario.local import ProveedorCalendarioLocal
from utilidades.archivos import asegurar_json, cargar, cargar_json, guardar_json
from utilidades.rutas import configurar_base_datos


class PersistenciaYMigracionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)

    def tearDown(self):
        configurar_base_datos(None)
        self.tmp.cleanup()

    def ruta(self, nombre):
        return os.path.join(self.tmp.name, nombre)

    def test_json_normal_bom_unicode_e_inexistente(self):
        normal = self.ruta("normal.json")
        bom = self.ruta("bom.json")
        inexistente = self.ruta("inexistente.json")
        guardar_json(normal, {"texto": "accion"})
        Path(bom).write_bytes(b'\xef\xbb\xbf{"texto": "caf\xc3\xa9"}')

        self.assertEqual(cargar(normal, {})["texto"], "accion")
        self.assertEqual(cargar(bom, {})["texto"], "cafe".replace("e", "é"))
        resultado = cargar_json(inexistente, {"defecto": True})
        self.assertFalse(resultado.existe)
        self.assertIsNone(resultado.error)

    def test_json_invalido_es_visible_y_no_se_sobrescribe(self):
        ruta = self.ruta("corrupto.json")
        original = b'{"sin_cerrar": true'
        Path(ruta).write_bytes(original)

        with self.assertLogs("utilidades.archivos", level="WARNING"):
            resultado = cargar_json(ruta, {"seguro": True})
        with self.assertLogs("utilidades.archivos", level="WARNING"):
            asegurar_json(ruta, {"seguro": True})

        self.assertIsNotNone(resultado.error)
        self.assertEqual(Path(ruta).read_bytes(), original)

    def test_guardado_elimina_bom(self):
        ruta = self.ruta("salida.json")
        guardar_json(ruta, {"unicode": "mañana"})
        self.assertFalse(Path(ruta).read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(cargar(ruta, {})["unicode"], "mañana")

    def test_migracion_recordatorios_es_idempotente_y_sin_fecha(self):
        calendario = self.ruta("calendario.json")
        proveedor = ProveedorCalendarioLocal(calendario)
        primer_origen = ["comprar pilas"]
        segundo_origen = ["comprar pilas"]

        primero = migrar_recordatorios_legacy(primer_origen, proveedor=proveedor)
        segundo = migrar_recordatorios_legacy(segundo_origen, proveedor=proveedor)
        recargado = ProveedorCalendarioLocal(calendario)

        self.assertEqual(primero, 1)
        self.assertEqual(segundo, 0)
        self.assertEqual(len(recargado.listar_eventos()), 1)
        evento = recargado.listar_eventos()[0]
        self.assertIsNone(evento.inicio)
        self.assertEqual(
            evento.metadatos["migracion"],
            "recordatorios_legacy_v1",
        )

    def test_migracion_no_escribe_si_calendario_esta_corrupto(self):
        calendario = self.ruta("calendario.json")
        original = b"{invalido"
        Path(calendario).write_bytes(original)
        with self.assertLogs("utilidades.archivos", level="WARNING"):
            proveedor = ProveedorCalendarioLocal(calendario)

        migrados = migrar_recordatorios_legacy(
            ["recordatorio"],
            proveedor=proveedor,
        )

        self.assertEqual(migrados, 0)
        self.assertEqual(Path(calendario).read_bytes(), original)

    @mock.patch("core.cerebro.generar_respuesta")
    def test_dominios_locales_invalidos_no_llaman_ia(self, generar):
        memoria = inicializar_memoria({})
        config = {"ia": {"activada": True}}

        for texto in (
            "nota",
            "memoria",
            "tarea",
            "recordatorio",
            "evento",
            "aplicacion",
            "mis aplicaciones",
            "borra tarea 1",
            "lista memorias",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(
                    procesar(texto, memoria, config).accion,
                    "ayuda_comando_local",
                )
        generar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
