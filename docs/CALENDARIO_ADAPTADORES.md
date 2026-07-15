# Adaptadores de calendario

ORION usa `ProveedorCalendario` como contrato comun para tareas, recordatorios y eventos. El proveedor local actual vive en `servicios/calendario/local.py` y guarda datos en JSON con campos listos para sincronizacion futura:

- `id`: identificador local estable.
- `proveedor`: proveedor actual, por ahora `local`.
- `proveedor_id`: identificador remoto opcional.
- `sincronizacion.estado`: `solo_local`, `sincronizado` o un estado futuro equivalente.
- `sincronizacion.ultima_sincronizacion`: fecha ISO opcional.
- `sincronizacion.conflicto`: indicador de conflicto.

Para agregar Google Calendar, Outlook, Notion u otro proveedor:

1. Crear un modulo nuevo, por ejemplo `servicios/calendario/google.py`.
2. Implementar los metodos de `ProveedorCalendario`: `crear_evento`, `listar_eventos`, `actualizar_evento`, `eliminar_evento`, `completar_tarea` y `sincronizar`.
3. Convertir los datos remotos hacia `EventoCalendario` sin cambiar `core/cerebro.py`.
4. Mantener el proveedor local como fuente offline y resolver conflictos usando los campos de `sincronizacion`.
5. Evitar que credenciales, tokens o rutas personales se guarden en archivos versionados.

El router de IA no debe ejecutar acciones ni escribir calendario directamente. Solo puede proponer texto o una accion estructurada que el cerebro valide.
