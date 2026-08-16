---
nombre: archivos
descripcion: Permite a ORION gestionar notas, recordatorios y datos persistentes locales.
---

# Archivos

## Cuándo utilizar
- cuando el usuario quiere crear, listar o borrar notas
- cuando el usuario quiere crear o gestionar recordatorios
- cuando el usuario quiere gestionar datos persistentes locales

## Herramientas relacionadas
- guardar_nota
- listar_notas
- borrar_nota
- crear_recordatorio
- persistencia_local

## Reglas
- los datos se guardan fuera del código, en el directorio de datos de ORION
- no escribir ni modificar archivos del proyecto
- la persistencia es atómica para evitar datos corruptos