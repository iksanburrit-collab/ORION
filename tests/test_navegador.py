import unittest
from unittest import mock

from comandos.navegador import navegador_inteligente


class NavegadorTests(unittest.TestCase):
    @mock.patch("comandos.navegador.webbrowser.open", return_value=True)
    def test_abre_busqueda_con_navegador_predeterminado(self, abrir):
        self.assertTrue(navegador_inteligente("busca clima en México"))
        abrir.assert_called_once_with("https://google.com/search?q=clima+en+m%C3%A9xico")

    @mock.patch("comandos.navegador.webbrowser.open", side_effect=OSError)
    def test_fallo_del_navegador_no_propaga_excepcion(self, abrir):
        self.assertFalse(navegador_inteligente("youtube gatos"))
        abrir.assert_called_once()

    def test_comando_desconocido_no_abre_nada(self):
        self.assertFalse(navegador_inteligente("musica"))


if __name__ == "__main__":
    unittest.main()
