import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.memoria import (
    construir_contexto_para_ia,
    inicializar_memoria,
)
from servicios.sistema.aplicaciones import CatalogoAplicaciones
from servicios.sistema.contratos import AplicacionRegistrada
from core.handlers.aplicaciones import procesar_aplicaciones
from utilidades.rutas import configurar_base_datos


class EstabilizacionSprintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        configurar_base_datos(self.tmp.name)
        self.cwd_original = os.getcwd()
        os.chdir(self.tmp.name)
        self.memoria = inicializar_memoria({})
        self.config = {
            "ia": {"activada": True},
            "sistema": {
                "control_pc_activado": True,
                "confirmar_riesgo_medio": True,
                "permitir_riesgo_alto": False,
            },
        }

    def tearDown(self):
        configurar_base_datos(None)
        os.chdir(self.cwd_original)
        self.tmp.cleanup()

    @mock.patch("core.cerebro.navegador_inteligente")
    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_busca_aplicacion_no_llama_navegador(self, generar, navegador):
        resultado = procesar("busca aplicacion chrome", self.memoria, self.config)

        self.assertEqual(resultado.accion, "buscar_aplicacion")
        navegador.assert_not_called()
        generar.assert_not_called()

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_que_fecha_es_no_llama_ia(self, generar):
        resultado = procesar("que fecha es", self.memoria, self.config)

        self.assertEqual(resultado.accion, "mostrar_fecha")
        generar.assert_not_called()

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_frases_de_fecha_y_hora_son_locales(self, generar):
        for texto in (
            "que fecha es",
            "que dia es hoy",
            "dime la fecha",
            "fecha actual",
            "en que fecha estamos",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(
                    procesar(texto, self.memoria, self.config).accion,
                    "mostrar_fecha",
                )
        self.assertEqual(
            procesar("que hora es", self.memoria, self.config).accion,
            "mostrar_hora",
        )
        generar.assert_not_called()

    @mock.patch("core.cerebro.navegador_inteligente", return_value=True)
    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_busqueda_web_generica_sigue_en_navegador(self, generar, navegador):
        resultado = procesar("busca clima de manana", self.memoria, self.config)

        self.assertEqual(resultado.accion, "navegador")
        navegador.assert_called_once()
        generar.assert_not_called()

    def test_recordatorio_no_lo_captura_notas_legacy(self):
        notas = []
        resultado = procesar(
            "recuerdame revisar backups manana",
            self.memoria,
            {"ia": {"activada": False}},
            notas=notas,
        )

        self.assertEqual(resultado.accion, "agregar_recordatorio")
        self.assertEqual(notas, [])

    @mock.patch("core.handlers.aplicaciones.platform.system", return_value="Windows")
    @mock.patch("core.handlers.aplicaciones.descubrir_aplicaciones_windows")
    def test_escanear_y_listar_usan_mismo_catalogo(self, descubrir, _sistema):
        ruta = os.path.join(self.tmp.name, "chrome.exe")
        Path(ruta).write_text("", encoding="utf-8")
        archivo = os.path.join(self.tmp.name, "apps.json")
        catalogo = CatalogoAplicaciones(archivo)
        descubrir.return_value = [
            AplicacionRegistrada(
                nombre="Chrome",
                aliases=["chrome"],
                ruta=ruta,
                origen="menu_inicio",
                verificada=True,
                ultima_deteccion="2026-07-15T00:00:00+00:00",
            )
        ]

        escaneo = procesar_aplicaciones(
            "escanea aplicaciones",
            self.config,
            catalogo=catalogo,
        )
        recargado = CatalogoAplicaciones(archivo)
        listado = procesar_aplicaciones(
            "lista aplicaciones",
            self.config,
            catalogo=recargado,
        )

        self.assertIn("Detectadas: 1", escaneo[2])
        self.assertIn("Nuevas: 1", escaneo[2])
        self.assertIn("Aplicaciones registradas: 1", listado[2])
        self.assertIn("Chrome", listado[2])

    def test_memorias_olvidadas_no_aparecen_en_listado_normal(self):
        procesar("me gusta minecraft", self.memoria, {"ia": {"activada": False}})
        procesar("olvida que me gusta minecraft", self.memoria, {"ia": {"activada": False}})

        resultado = procesar("mis memorias", self.memoria, {"ia": {"activada": False}})
        olvidadas = procesar("memorias olvidadas", self.memoria, {"ia": {"activada": False}})

        self.assertNotIn("Minecraft", resultado.respuesta)
        self.assertIn("minecraft", olvidadas.respuesta.lower())

    def test_memorias_olvidadas_no_aparecen_en_contexto_ia(self):
        procesar("me gusta minecraft", self.memoria, {"ia": {"activada": False}})
        procesar("olvida que me gusta minecraft", self.memoria, {"ia": {"activada": False}})

        contexto = construir_contexto_para_ia(self.memoria, consulta="minecraft")

        self.assertNotIn("Minecraft", contexto)
        self.assertNotIn("olvido", contexto)

    @mock.patch("core.handlers.ia.generar_respuesta")
    def test_comandos_antiguos_siguen_funcionando(self, generar):
        hora = procesar("hora", self.memoria, self.config)
        nota = procesar(
            "recuerda comprar leche",
            self.memoria,
            self.config,
            notas=[],
        )

        self.assertEqual(hora.accion, "mostrar_hora")
        self.assertEqual(nota.accion, "guardar_nota")
        generar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
