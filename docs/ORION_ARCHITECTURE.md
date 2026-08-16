# ORION

## Objetivo

ORION es un asistente personal desarrollado en Python.

Su propósito es ayudar al usuario en tareas diarias, recordar información importante, automatizar procesos y evolucionar hasta convertirse en el centro de un sistema inteligente.

---

# Arquitectura

Actualmente:

main.py

Responsable de:

- Iniciar ORION
- Cargar datos
- Esperar comandos
- Ejecutar acciones
- Responder al usuario

---

# Módulos

## core

Responsabilidad:

Núcleo inteligente.

Actualmente contiene:

- cerebro.py: orquesta intenciones y proveedores de IA.
- handlers/: resolvers por intención (aplicaciones, tareas, configuración, alias, notas, registro, memoria).
- memoria/: memoria persistente, episódica y conversacional.
- conocimiento/: normalización, clasificación y detección de conocimiento.
- intenciones.py: detección de intenciones.
- personalidad.py: adapta el tono de las respuestas.

---

## comandos

Responsabilidad:

Comandos locales y seguridad.

Actualmente contiene:

- calculadora.py: evaluación segura por AST.
- navegador.py: apertura del navegador con URLs fijas.

---

## ia

Responsabilidad:

Proveedores de IA opcionales.

Actualmente contiene:

- proveedor.py: router con orden y respaldo entre proveedores.
- groq.py: adaptador de Groq.
- ollama.py: adaptador de Ollama.

---

## servicios

Responsabilidad:

Servicios de dominio.

Actualmente contiene:

- calendario/: tareas, recordatorios y eventos con proveedor local.
- sistema/: control del PC, permisos y catálogo de aplicaciones.
- notas.py: repositorio de notas.

---

## utilidades

Responsabilidad:

Funciones reutilizables.

Actualmente contiene:

- rutas.py: resolución del directorio de datos.
- archivos.py: carga y guardado atómico en JSON.
- entorno.py: carga de variables desde .env.
- texto.py: normalización de texto.
- fechas.py: utilidades de fecha y hora.

---

Versión:

v2.0