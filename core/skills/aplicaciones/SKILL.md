---
nombre: aplicaciones
descripcion: Permite a ORION trabajar con aplicaciones instaladas en el sistema.
---

# Aplicaciones

## Cuándo utilizar
- cuando el usuario quiere abrir una aplicación
- cuando el usuario quiere cerrar una aplicación
- cuando el usuario quiere consultar o buscar aplicaciones disponibles
- cuando el usuario quiere escanear o actualizar el catálogo de aplicaciones

## Herramientas relacionadas
- abrir_aplicacion
- cerrar_aplicacion
- buscar_aplicacion
- listar_aplicaciones
- escanear_aplicaciones

## Reglas
- no asumir nombres de ejecutables; verificar primero qué aplicación está disponible
- solo se abre una aplicación registrada en el catálogo
- el descubrimiento automático solo está implementado en Windows
- las acciones sobre aplicaciones requieren que el control del PC esté activado