# Tools en ORION

Una Tool es una acción ejecutable que ORION puede invocar de forma segura. A
diferencia de una Skill (que describe una capacidad de forma declarativa y no
ejecuta nada), una Tool tiene un contrato con parámetros, valida la entrada y
ejecuta una acción real del sistema pasando siempre por la puerta de permisos.

## Arquitectura

```
core/tools/
    contratos.py              # Tool, Parametro, ToolResult, ToolError, validar_parametros
    registro.py               # ToolRegistry y helpers de módulo
    herramientas/
        aplicaciones.py       # abrir_aplicacion, listar_aplicaciones
        navegador.py          # abrir_navegador
```

Cada Tool se define con:

- `name`: nombre único, usado como identificador.
- `description`: descripción breve de la acción.
- `parametros`: esquema de parámetros con tipo y si son requeridos.
- `ejecutor`: función que recibe los parámetros validados y devuelve un
  `ToolResult`.

`validar_parametros` comprueba que los parámetros requeridos estén presentes y
con el tipo correcto. Un `ToolResult` indica `exito`, `mensaje`, `datos`
opcionales y `tipo_error` para fallos explícitos.

## Tools disponibles

| Tool                | Descripción                                            |
|---------------------|--------------------------------------------------------|
| `abrir_aplicacion`  | Abre una aplicación registrada en el catálogo.         |
| `listar_aplicaciones` | Devuelve las aplicaciones disponibles con sus alias. |
| `abrir_navegador`   | Abre el navegador con una búsqueda web o un navegador concreto. |

## Uso

```python
from core.tools import ejecutar_herramienta, herramientas_disponibles

herramientas_disponibles()                       # ["abrir_aplicacion", ...]
resultado = ejecutar_herramienta(
    "abrir_aplicacion",
    {"aplicacion": "brave", "config": config},
)
print(resultado.exito, resultado.mensaje)
```

## Registro

```python
from core.tools import ToolRegistry

registro = ToolRegistry()
registro.descubrir()             # registra las Tools base
registro.nombres()               # ["abrir_aplicacion", "abrir_navegador", "listar_aplicaciones"]
registro.obtener("abrir_navegador")
registro.ejecutar("abrir_aplicacion", {"aplicacion": "brave"})
```

## Descubrimiento de aplicaciones

ORION no asume nombres de ejecutables. El catálogo se completa de dos formas:

1. **Manual**: `CatalogoAplicaciones().agregar_manual(nombre, ruta, aliases)`.
2. **Automático** (comando "escanea aplicaciones"):
   - En **Windows** se leen los accesos directos del menú de inicio.
   - En **Linux** se leen los archivos `.desktop` de las rutas XDG
     (`$XDG_DATA_HOME/applications`, `~/.local/share/applications` y
     `$XDG_DATA_DIRS/applications`).

El resolutor de nombres normaliza la entrada (minúsculas, sin acentos) y busca
por nombre o alias. Aplicaciones comunes como Brave, Firefox, Steam o VS Code
reciben alias reconocibles (`brave`, `firefox`, `steam`, `vscode`, `code`).

## Seguridad

- Las Tools no usan `shell=True` ni construyen comandos desde la entrada del
  usuario. La entrada se resuelve contra el catálogo y, solo si existe una
  aplicación registrada, se lanza su ruta conocida.
- `ruta_permitida` rechaza rutas con metacaracteres de shell (`;`, `&`, `|`,
  `<`, `>`).
- Toda ejecución pasa por `EjecutorAccionesPC`, que aplica la política de
  permisos (`control_pc_activado`, `permitir_riesgo_alto`). Con el control del
  PC desactivado, las acciones se bloquean.
- No existe agente, planificación ni selección por LLM: los comandos del
  usuario se enrutan a la Tool correspondiente de forma determinista.

## Fuera de esta fase

- Agente autónomo y razonamiento ReAct.
- Selección de Tools mediante LLM.
- Instalación dinámica de Tools o sistema de plugins.
- Automatización de pestañas o control fino del navegador.