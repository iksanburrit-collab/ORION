import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.cerebro import procesar
from core.memoria import inicializar_memoria
from core.tools import (
    Tool,
    ToolError,
    ToolRegistry,
    ejecutar_herramienta,
    herramientas_disponibles,
    obtener_herramienta,
)
from core.tools.contratos import ToolResult
from servicios.sistema.aplicaciones import CatalogoAplicaciones
from servicios.sistema.descubrimiento_linux import descubrir_aplicaciones_linux
from utilidades.rutas import configurar_base_datos


def config_con_control_pc() -> dict:
    return {
        "ia": {"activada": False},
        "sistema": {
            "control_pc_activado": True,
            "confirmar_riesgo_medio": True,
            "permitir_riesgo_alto": False,
        },
    }


def _escribir_desktop(carpeta: Path, nombre: str, contenido: str) -> Path:
    ruta = carpeta / f"{nombre}.desktop"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


class RegistroToolsTests(unittest.TestCase):
    def test_descubre_las_tools_iniciales(self):
        registro = ToolRegistry()
        nombres = {tool.name for tool in registro.descubrir()}
        self.assertEqual(
            nombres,
            {"abrir_aplicacion", "listar_aplicaciones", "abrir_navegador"},
        )

    def test_nombres_esta_ordenado(self):
        registro = ToolRegistry()
        self.assertEqual(
            registro.nombres(),
            ["abrir_aplicacion", "abrir_navegador", "listar_aplicaciones"],
        )

    def test_obtener_por_nombre(self):
        registro = ToolRegistry()
        self.assertEqual(registro.obtener("abrir_aplicacion").name, "abrir_aplicacion")
        self.assertTrue(registro.obtener("listar_aplicaciones").description)

    def test_existe_y_no_existe(self):
        registro = ToolRegistry()
        self.assertTrue(registro.existe("abrir_navegador"))
        self.assertFalse(registro.existe("tool_inexistente"))
        with self.assertRaises(ToolError):
            registro.obtener("tool_inexistente")

    def test_registrar_una_tool_nueva(self):
        registro = ToolRegistry()
        registro.registrar(
            Tool(
                name="tool_prueba",
                description="Tool de prueba",
                ejecutor=lambda: ToolResult(True, "ok", "tool_prueba"),
            )
        )
        self.assertTrue(registro.existe("tool_prueba"))

    def test_registrar_duplicado_levanta_error(self):
        registro = ToolRegistry()
        registro.descubrir()
        with self.assertRaises(ToolError):
            registro.registrar(
                Tool(
                    name="abrir_aplicacion",
                    description="Duplicado",
                    ejecutor=lambda: ToolResult(True, "", "abrir_aplicacion"),
                )
            )

    def test_registrar_duplicado_en_registro_nuevo_levanta_error(self):
        registro = ToolRegistry()
        with self.assertRaises(ToolError):
            registro.registrar(
                Tool(
                    name="abrir_navegador",
                    description="Intenta reemplazar la base",
                    ejecutor=lambda: ToolResult(True, "", "abrir_navegador"),
                )
            )

    def test_listar_en_registro_nuevo_descubre_base(self):
        registro = ToolRegistry()
        nombres = {tool.name for tool in registro.listar()}
        self.assertEqual(
            nombres,
            {"abrir_aplicacion", "listar_aplicaciones", "abrir_navegador"},
        )

    def test_nombres_en_registro_nuevo_descubre_base(self):
        registro = ToolRegistry()
        self.assertEqual(
            registro.nombres(),
            ["abrir_aplicacion", "abrir_navegador", "listar_aplicaciones"],
        )

    def test_obtener_en_registro_nuevo_descubre_base(self):
        registro = ToolRegistry()
        self.assertEqual(registro.obtener("listar_aplicaciones").name, "listar_aplicaciones")
        self.assertEqual(
            registro.obtener("abrir_navegador").name,
            "abrir_navegador",
        )

    def test_descubrir_repetido_es_idempotente(self):
        registro = ToolRegistry()
        primera = registro.descubrir()
        segunda = registro.descubrir()
        self.assertEqual({tool.name for tool in primera}, {tool.name for tool in segunda})
        self.assertEqual(
            registro.nombres(),
            ["abrir_aplicacion", "abrir_navegador", "listar_aplicaciones"],
        )

    def test_sin_duplicados_tras_descubrir_y_listar(self):
        registro = ToolRegistry()
        registro.descubrir()
        registro.descubrir()
        registro.listar()
        registro.nombres()
        nombres = registro.nombres()
        self.assertEqual(len(nombres), len(set(nombres)))
        self.assertEqual(len(nombres), 3)

    def test_registrar_custom_junto_a_base_sin_duplicados(self):
        registro = ToolRegistry()
        registro.registrar(
            Tool(
                name="tool_custom",
                description="Tool de usuario",
                ejecutor=lambda: ToolResult(True, "ok", "tool_custom"),
            )
        )
        self.assertEqual(len(registro.nombres()), 4)
        self.assertEqual(len(registro.nombres()), len(set(registro.nombres())))

    def test_helpers_de_modulo_consultables(self):
        self.assertIn("abrir_aplicacion", herramientas_disponibles())
        self.assertEqual(obtener_herramienta("abrir_navegador").name, "abrir_navegador")


class ValidacionParametrosTests(unittest.TestCase):
    def test_falta_parametro_requerido(self):
        resultado = ejecutar_herramienta("abrir_aplicacion", {})
        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "parametros_invalidos")

    def test_parametro_requerido_nulo(self):
        resultado = ejecutar_herramienta("abrir_aplicacion", {"aplicacion": None})
        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "parametros_invalidos")

    def test_tipo_de_parametro_incorrecto(self):
        resultado = ejecutar_herramienta("abrir_aplicacion", {"aplicacion": 42})
        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "parametros_invalidos")


class ListarAplicacionesTests(unittest.TestCase):
    def test_lista_aplicaciones_estructuradas(self):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                ruta = Path(temporal) / "brave.desktop"
                ruta.write_text("", encoding="utf-8")
                catalogo = CatalogoAplicaciones()
                catalogo.agregar_manual("Brave Browser", str(ruta), ["brave"])

                resultado = ejecutar_herramienta(
                    "listar_aplicaciones", {"catalogo": catalogo}
                )
                self.assertTrue(resultado.exito)
                apps = resultado.datos["aplicaciones"]
                self.assertEqual(len(apps), 1)

                app = apps[0]
                self.assertEqual(app["nombre"], "Brave Browser")
                self.assertEqual(app["identificador"], "brave browser")
                self.assertEqual(app["comando"], str(ruta))
                self.assertIn("brave", app["alias"])
            finally:
                configurar_base_datos(None)


class ResolucionNombresTests(unittest.TestCase):
    def _catalogo_en_tmp(self, temporal: str, nombre: str, ruta: Path, aliases) -> CatalogoAplicaciones:
        catalogo = CatalogoAplicaciones()
        catalogo.agregar_manual(nombre, str(ruta), aliases)
        return catalogo

    def test_resuelve_brave_por_nombre_y_alias(self):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                ruta = Path(temporal) / "brave.desktop"
                ruta.write_text("", encoding="utf-8")
                catalogo = self._catalogo_en_tmp(temporal, "Brave Browser", ruta, ["brave"])

                self.assertEqual(catalogo.buscar_para_usuario("brave").nombre, "Brave Browser")
                self.assertEqual(catalogo.buscar_para_usuario("Brave Browser").nombre, "Brave Browser")
            finally:
                configurar_base_datos(None)

    def test_resuelve_vscode_por_aliases_comunes(self):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                ruta = Path(temporal) / "code.desktop"
                ruta.write_text("", encoding="utf-8")
                catalogo = self._catalogo_en_tmp(
                    temporal, "Visual Studio Code", ruta, ["vscode", "code"]
                )

                self.assertEqual(catalogo.buscar_para_usuario("vscode").nombre, "Visual Studio Code")
                self.assertEqual(catalogo.buscar_para_usuario("code").nombre, "Visual Studio Code")
            finally:
                configurar_base_datos(None)


class DescubrimientoLinuxTests(unittest.TestCase):
    def test_descubre_desktop_files_de_linux(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal) / "applications"
            carpeta.mkdir()
            _escribir_desktop(
                carpeta,
                "brave-browser",
                "[Desktop Entry]\nType=Application\nName=Brave Browser\nExec=brave-browser %U\n",
            )
            _escribir_desktop(
                carpeta,
                "oculta",
                "[Desktop Entry]\nType=Application\nName=Oculta\nNoDisplay=true\n",
            )
            _escribir_desktop(
                carpeta,
                "enlace",
                "[Desktop Entry]\nType=Link\nName=Enlace\n",
            )

            apps = descubrir_aplicaciones_linux([carpeta])
            self.assertEqual({app.nombre for app in apps}, {"Brave Browser"})

            brave = next(app for app in apps if app.nombre == "Brave Browser")
            self.assertIn("brave", brave.aliases)
            self.assertEqual(brave.origen, "desktop")
            self.assertTrue(brave.verificada)

    def test_carpeta_inexistente_devuelve_vacio(self):
        self.assertEqual(descubrir_aplicaciones_linux([Path("/no/existe")]), [])

    def test_resuelve_brave_descubierto(self):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                carpeta = Path(temporal) / "applications"
                carpeta.mkdir()
                _escribir_desktop(
                    carpeta,
                    "brave-browser",
                    "[Desktop Entry]\nType=Application\nName=Brave Browser\nExec=brave-browser %U\n",
                )

                catalogo = CatalogoAplicaciones()
                catalogo.actualizar_desde_descubrimiento(
                    descubrir_aplicaciones_linux([carpeta])
                )
                self.assertEqual(catalogo.buscar_para_usuario("brave").nombre, "Brave Browser")
                self.assertEqual(catalogo.buscar_para_usuario("firefox"), None)
            finally:
                configurar_base_datos(None)


class EjecucionAplicacionesTests(unittest.TestCase):
    @mock.patch("servicios.sistema.acciones_pc.shutil.which", return_value="/usr/bin/xdg-open")
    @mock.patch("servicios.sistema.acciones_pc.subprocess.Popen")
    def test_abre_aplicacion_conocida_sin_shell(self, popen, which):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                ruta = Path(temporal) / "brave.desktop"
                ruta.write_text("", encoding="utf-8")
                CatalogoAplicaciones().agregar_manual("Brave Browser", str(ruta), ["brave"])

                resultado = ejecutar_herramienta(
                    "abrir_aplicacion",
                    {"aplicacion": "brave", "config": config_con_control_pc()},
                )
                self.assertTrue(resultado.exito)
                self.assertIn("Abriendo Brave Browser", resultado.mensaje)
                popen.assert_called_once()
                args, kwargs = popen.call_args
                self.assertEqual(args[0], ["/usr/bin/xdg-open", str(ruta)])
                self.assertFalse(kwargs["shell"])
                self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
                self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
            finally:
                configurar_base_datos(None)

    def test_rechaza_aplicacion_ficticia(self):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                resultado = ejecutar_herramienta(
                    "abrir_aplicacion",
                    {"aplicacion": "app que no existe", "config": config_con_control_pc()},
                )
                self.assertFalse(resultado.exito)
                self.assertEqual(resultado.tipo_error, "aplicacion_no_registrada")
            finally:
                configurar_base_datos(None)

    def test_rechaza_ejecucion_arbitraria(self):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                resultado = ejecutar_herramienta(
                    "abrir_aplicacion",
                    {"aplicacion": "; rm -rf /", "config": config_con_control_pc()},
                )
                self.assertFalse(resultado.exito)
                self.assertEqual(resultado.tipo_error, "aplicacion_no_registrada")
            finally:
                configurar_base_datos(None)

    def test_no_se_registra_ruta_con_comandos(self):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                catalogo = CatalogoAplicaciones()
                with self.assertRaises(ValueError):
                    catalogo.agregar_manual("Maliciosa", "/usr/bin/app; rm -rf /")
            finally:
                configurar_base_datos(None)

    def test_control_pc_desactivado_bloquea_apertura(self):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                ruta = Path(temporal) / "brave.desktop"
                ruta.write_text("", encoding="utf-8")
                CatalogoAplicaciones().agregar_manual("Brave Browser", str(ruta), ["brave"])

                resultado = ejecutar_herramienta(
                    "abrir_aplicacion",
                    {"aplicacion": "brave", "config": {"sistema": {"control_pc_activado": False}}},
                )
                self.assertFalse(resultado.exito)
                self.assertIn("desactivado", resultado.mensaje.lower())
            finally:
                configurar_base_datos(None)


class NavegadorTests(unittest.TestCase):
    @mock.patch("core.tools.herramientas.navegador.navegador_inteligente", return_value=True)
    def test_abrir_navegador_con_consulta(self, navegador):
        resultado = ejecutar_herramienta("abrir_navegador", {"consulta": "busca gatos"})
        self.assertTrue(resultado.exito)
        navegador.assert_called_once_with("busca gatos")

    @mock.patch("core.tools.herramientas.navegador.navegador_inteligente", return_value=False)
    def test_abrir_navegador_falla_con_error_explicito(self, navegador):
        resultado = ejecutar_herramienta("abrir_navegador", {"consulta": "busca gatos"})
        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "error_navegador")

    def test_abrir_navegador_sin_parametros_validos(self):
        resultado = ejecutar_herramienta("abrir_navegador", {})
        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.tipo_error, "error_navegador")

    @mock.patch("servicios.sistema.acciones_pc.shutil.which", return_value="/usr/bin/xdg-open")
    @mock.patch("servicios.sistema.acciones_pc.subprocess.Popen")
    def test_abrir_navegador_especifico_reusa_aplicaciones(self, popen, which):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                ruta = Path(temporal) / "brave.desktop"
                ruta.write_text("", encoding="utf-8")
                CatalogoAplicaciones().agregar_manual("Brave Browser", str(ruta), ["brave"])

                resultado = ejecutar_herramienta(
                    "abrir_navegador",
                    {"aplicacion": "brave", "config": config_con_control_pc()},
                )
                self.assertTrue(resultado.exito)
                popen.assert_called_once()
            finally:
                configurar_base_datos(None)


class IntegracionOrionTests(unittest.TestCase):
    @mock.patch("servicios.sistema.acciones_pc.shutil.which", return_value="/usr/bin/xdg-open")
    @mock.patch("servicios.sistema.acciones_pc.subprocess.Popen")
    def test_procesar_abre_brave_usa_la_tool(self, popen, which):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                ruta = Path(temporal) / "brave.desktop"
                ruta.write_text("", encoding="utf-8")
                CatalogoAplicaciones().agregar_manual("Brave Browser", str(ruta), ["brave"])

                memoria = inicializar_memoria({})
                resultado = procesar("abre brave", memoria, config_con_control_pc())

                self.assertEqual(resultado.accion, "abrir_aplicacion")
                self.assertIn("Abriendo Brave Browser", resultado.respuesta)
                popen.assert_called_once()
            finally:
                configurar_base_datos(None)


class DescubrimientoAutomaticoCatalogoTests(unittest.TestCase):
    def _carpeta_con_apps(self, temporal: str) -> Path:
        carpeta = Path(temporal) / "applications"
        carpeta.mkdir(exist_ok=True)
        _escribir_desktop(
            carpeta,
            "brave-browser",
            "[Desktop Entry]\nType=Application\nName=Brave Browser\nExec=brave-browser %U\n",
        )
        _escribir_desktop(
            carpeta,
            "firefox",
            "[Desktop Entry]\nType=Application\nName=Firefox\nExec=firefox %U\n",
        )
        return carpeta

    @mock.patch("servicios.sistema.aplicaciones.platform.system", return_value="Linux")
    @mock.patch("servicios.sistema.descubrimiento_linux._carpetas_aplicaciones")
    def test_catalogo_descubre_aplicaciones_linux(self, carpetas, _sistema):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                carpetas.return_value = [self._carpeta_con_apps(temporal)]

                catalogo = CatalogoAplicaciones()
                apps = catalogo.listar()

                self.assertEqual(len(apps), 2)
                self.assertEqual(apps[0].nombre, "Brave Browser")
                self.assertEqual(apps[1].nombre, "Firefox")
                self.assertEqual(apps[0].origen, "desktop")
                self.assertTrue(apps[0].verificada)
            finally:
                configurar_base_datos(None)

    @mock.patch("servicios.sistema.aplicaciones.platform.system", return_value="Linux")
    @mock.patch("servicios.sistema.descubrimiento_linux._carpetas_aplicaciones")
    def test_catalogo_no_re_descubre_en_la_misma_instancia(self, carpetas, _sistema):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                carpetas.return_value = [self._carpeta_con_apps(temporal)]

                catalogo = CatalogoAplicaciones()
                catalogo.listar()
                catalogo.listar()
                catalogo.buscar_para_usuario("brave")

                self.assertEqual(carpetas.call_count, 1)
                self.assertEqual(catalogo.buscar_para_usuario("brave").nombre, "Brave Browser")
            finally:
                configurar_base_datos(None)

    @mock.patch("servicios.sistema.aplicaciones.platform.system", return_value="Linux")
    def test_catalogo_con_registros_no_auto_descubre_ni_duplica(self, _sistema):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                ruta = Path(temporal) / "app.exe"
                ruta.write_text("", encoding="utf-8")
                CatalogoAplicaciones().agregar_manual("App Manual", str(ruta), ["app"])

                catalogo = CatalogoAplicaciones()
                apps = catalogo.listar()

                self.assertEqual(len(apps), 1)
                self.assertEqual(apps[0].nombre, "App Manual")
            finally:
                configurar_base_datos(None)


class ListarAplicacionesDescubiertasTests(unittest.TestCase):
    @mock.patch("servicios.sistema.aplicaciones.platform.system", return_value="Linux")
    @mock.patch("servicios.sistema.descubrimiento_linux._carpetas_aplicaciones")
    def test_listar_aplicaciones_devuelve_descubiertas(self, carpetas, _sistema):
        with tempfile.TemporaryDirectory() as temporal:
            configurar_base_datos(temporal)
            try:
                carpeta = Path(temporal) / "applications"
                carpeta.mkdir()
                _escribir_desktop(
                    carpeta,
                    "brave-browser",
                    "[Desktop Entry]\nType=Application\nName=Brave Browser\nExec=brave-browser %U\n",
                )
                _escribir_desktop(
                    carpeta,
                    "steam",
                    "[Desktop Entry]\nType=Application\nName=Steam\nExec=steam %U\n",
                )
                carpetas.return_value = [carpeta]

                resultado = ejecutar_herramienta("listar_aplicaciones")

                self.assertTrue(resultado.exito)
                aplicaciones = resultado.datos["aplicaciones"]
                nombres = {app["nombre"] for app in aplicaciones}
                self.assertEqual(nombres, {"Brave Browser", "Steam"})

                brave = next(
                    app for app in aplicaciones if app["nombre"] == "Brave Browser"
                )
                self.assertEqual(brave["origen"], "desktop")
                self.assertIn("brave", brave["alias"])
                self.assertTrue(brave["comando"].endswith(".desktop"))
            finally:
                configurar_base_datos(None)


if __name__ == "__main__":
    unittest.main()