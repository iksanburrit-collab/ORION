import os
import tempfile
import unittest
from pathlib import Path

from utilidades.entorno import cargar_entorno


class EntornoTests(unittest.TestCase):
    def test_carga_variables_y_respeta_el_entorno_existente(self):
        with tempfile.TemporaryDirectory() as temporal:
            archivo = Path(temporal) / ".env"
            archivo.write_text(
                "# comentario\nGROQ_API_KEY=desde_archivo\nexport OTRO_VALOR='activo'\n",
                encoding="utf-8",
            )
            anterior_clave = os.environ.get("GROQ_API_KEY")
            anterior_otro = os.environ.get("OTRO_VALOR")
            os.environ["GROQ_API_KEY"] = "desde_entorno"
            try:
                cargar_entorno(archivo)
                self.assertEqual(os.environ["GROQ_API_KEY"], "desde_entorno")
                self.assertEqual(os.environ["OTRO_VALOR"], "activo")
            finally:
                if anterior_clave is None:
                    os.environ.pop("GROQ_API_KEY", None)
                else:
                    os.environ["GROQ_API_KEY"] = anterior_clave
                if anterior_otro is None:
                    os.environ.pop("OTRO_VALOR", None)
                else:
                    os.environ["OTRO_VALOR"] = anterior_otro


if __name__ == "__main__":
    unittest.main()
