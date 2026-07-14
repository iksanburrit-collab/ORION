# Proveedores de IA en ORION

ORION usa un router simple de proveedores. El cerebro solo llama a
`generar_respuesta(...)`; el orden, los fallos y el respaldo se resuelven en
`ia/proveedor.py`.

## Arquitectura

El flujo predeterminado es:

1. `groq`: proveedor cloud principal.
2. `ollama`: respaldo local y offline.

Cada adaptador recibe una `SolicitudIA` y devuelve una `RespuestaIA`, definidas
en `ia/contratos.py`.

## Configuracion

La configuracion recomendada es:

```json
{
  "ia": {
    "activada": true,
    "router": {
      "orden_proveedores": ["groq", "ollama"]
    },
    "proveedores": {
      "groq": {
        "activado": true,
        "modelo": "llama-3.1-8b-instant",
        "timeout": 15,
        "max_tokens": 180,
        "temperature": 0.6,
        "top_p": 0.9
      },
      "ollama": {
        "activado": true,
        "modelo": "qwen3:1.7b",
        "timeout": 45,
        "keep_alive": "10m",
        "num_predict": 90,
        "num_ctx": 2048
      },
      "futuro": {
        "activado": false,
        "tipo": "",
        "modelo": ""
      }
    },
    "limite_contexto": 700,
    "max_turnos": 4,
    "debug_rendimiento": false
  }
}
```

## Establecer GROQ_API_KEY en Windows

En PowerShell:

```powershell
setx GROQ_API_KEY "tu_clave"
```

Cierra y abre de nuevo la terminal antes de iniciar ORION. La clave se lee solo
desde la variable de entorno y no debe guardarse en `config.json`.

## Elegir modelo de Groq

Cambia este valor en `config.json`:

```json
"modelo": "llama-3.1-8b-instant"
```

Usa un modelo disponible en tu cuenta de Groq. No necesitas tocar Python para
cambiarlo.

## Usar Solo Ollama

Configura el orden y desactiva Groq:

```json
"router": {
  "orden_proveedores": ["ollama"]
},
"proveedores": {
  "groq": {
    "activado": false
  },
  "ollama": {
    "activado": true
  }
}
```

## Desactivar IA

```json
"activada": false
```

Los comandos internos, aprendizaje, perfil, fecha, hora y memoria siguen
funcionando sin llamar al router de IA.

## Agregar Otro Proveedor

1. Copia `ia/plantilla_proveedor.py.example` como `ia/nuevo_proveedor.py`.
2. Implementa `responder(solicitud: SolicitudIA) -> RespuestaIA`.
3. Registra el adaptador en `ia/proveedor.py`:

```python
PROVEEDORES["nuevo"] = nuevo_proveedor.responder
```

4. Agrega su bloque en `config["ia"]["proveedores"]`.
5. Agrega el nombre al orden del router.
6. Crea tests con mocks de `urllib.request.urlopen`.

No hagas llamadas reales en tests y no guardes claves en archivos del proyecto.

## Tests

Los tests de proveedores usan mocks. Deben validar payloads, errores HTTP,
timeouts, respuesta vacia, JSON invalido, orden de fallback y que las metricas
no expongan claves.

