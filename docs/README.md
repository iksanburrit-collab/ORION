# 🛰️ ORION

<div align="center">

# ORION

### Asistente de Inteligencia Artificial Personal desarrollado en Python

**Memoria • Automatización • Lenguaje Natural • IA Local • IA en la Nube**

> *"Un asistente que entiende, recuerda y actúa."*

</div>

---

# 📖 ¿Qué es ORION?

ORION es un asistente de inteligencia artificial desarrollado desde cero en Python con una arquitectura modular.

Su objetivo es evolucionar hasta convertirse en un verdadero asistente personal capaz de comprender lenguaje natural, recordar información importante, automatizar tareas, controlar el equipo, interactuar con distintos modelos de IA y funcionar en múltiples plataformas utilizando un único núcleo inteligente.

A diferencia de un chatbot tradicional, ORION busca realizar la mayor cantidad posible de tareas de forma local y recurrir a servicios de inteligencia artificial únicamente cuando sea realmente necesario.

---

# ✨ Características actuales

## 🧠 Memoria

* Memoria persistente.
* Memoria conversacional.
* Perfil del usuario.
* Aprendizaje de información importante.
* Gestión de conocimientos.

---

## 📝 Organización

* Sistema de notas.
* Sistema de recordatorios.
* Gestión de tareas.
* Alias personalizados.

---

## 🤖 Inteligencia Artificial

* Integración con Groq.
* Integración con Ollama.
* Selección automática del proveedor de IA.
* Prioridad a la ejecución local.

---

## 💻 Control del sistema

* Apertura segura de aplicaciones.
* Comandos locales.
* Arquitectura modular basada en servicios.

---

## 🏗️ Arquitectura

* Diseño modular.
* Separación por componentes.
* Sistema de handlers.
* Fácil mantenimiento.
* Escalable para futuras funciones.

---

# 📂 Estructura del proyecto

```text
ORION/
│
├── comandos/
│
├── core/
│   ├── cerebro.py
│   ├── handlers/
│   ├── memoria.py
│   ├── personalidad.py
│   └── ...
│
├── ia/
│   ├── proveedor.py
│   ├── groq.py
│   ├── ollama.py
│   └── ...
│
├── servicios/
│   ├── calendario/
│   ├── sistema/
│   └── ...
│
├── utilidades/
│
├── docs/
│
├── tests/
│
├── main.py
│
└── README.md
```

---

# 🧠 Arquitectura general

```text
                    Usuario
                       │
                       ▼
               ┌────────────────┐
               │  Core ORION    │
               │  cerebro.py    │
               └────────┬───────┘
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
     Memoria      Comandos Locales    Router IA
        │               │                │
        ▼               ▼                ▼
Notas y Perfil   Aplicaciones       Groq
Recordatorios    Sistema            Ollama
Tareas
```

---

# 🚀 Instalación

Clona el repositorio:

```bash
git clone https://github.com/iksanburrit-collab/ORION.git

cd ORION
```

Instala las dependencias:

```bash
pip install -r requirements.txt
```

Crea un archivo `.env` utilizando como base el archivo `.env.example`.

Dentro del archivo coloca tu clave:

```env
GROQ_API_KEY=TU_API_KEY
```

Finalmente ejecuta ORION:

```bash
python main.py
```

---

# 💬 Ejemplos de uso

```text
ORION> recuerda que mi color favorito es azul

✔ Información guardada correctamente.

ORION> ¿Cuál es mi color favorito?

Tu color favorito es azul.
```

---

```text
ORION> abre Discord

¿Deseas abrir Discord?

> sí

Abriendo Discord...
```

---

```text
ORION> crea un recordatorio mañana a las 8:00

✔ Recordatorio creado correctamente.
```

---

# ⚙️ Tecnologías utilizadas

* Python
* JSON
* Groq API
* Ollama
* Arquitectura modular
* Procesamiento de lenguaje natural

---

# 🎯 Objetivos del proyecto

ORION está siendo desarrollado para convertirse en un asistente capaz de:

* Comprender lenguaje natural.
* Recordar conversaciones importantes.
* Aprender gustos y preferencias.
* Gestionar tareas.
* Administrar notas.
* Crear recordatorios.
* Controlar aplicaciones del equipo.
* Automatizar acciones repetitivas.
* Trabajar con múltiples proveedores de IA.
* Ejecutar la mayor cantidad posible de procesos de forma local.

---

# 🛣️ Hoja de ruta

## Núcleo

* ✅ Memoria persistente.
* ✅ Memoria conversacional.
* ✅ Sistema de notas.
* ✅ Sistema de recordatorios.
* ✅ Gestión de tareas.
* ✅ Sistema de alias.
* ✅ Arquitectura modular.

---

## Inteligencia Artificial

* ✅ Integración con Groq.
* ✅ Integración con Ollama.
* ✅ Router de IA.
* ⏳ Optimización automática de proveedores.
* ⏳ RAG local.
* ⏳ Modelos con visión.
* ⏳ Reconocimiento de voz.
* ⏳ Síntesis de voz.

---

## Productividad

* ⏳ Google Calendar.
* ⏳ Gmail.
* ⏳ Google Drive.
* ⏳ Outlook.
* ⏳ Lectura de PDF.
* ⏳ Word.
* ⏳ Excel.

---

## Automatización

* ⏳ Control avanzado de Windows.
* ⏳ Adaptador para Linux.
* ⏳ Adaptador para macOS.
* ⏳ Adaptador para Android.
* ⏳ Adaptador para iOS.

---

## Visión a largo plazo

* ⏳ Asistente multiplataforma.
* ⏳ Sistema de plugins.
* ⏳ Agentes autónomos.
* ⏳ Automatización inteligente.
* ⏳ Asistente digital completamente conversacional.

---

# 🏛️ Filosofía de ORION

ORION se desarrolla bajo cinco principios fundamentales.

### 🗣️ Lenguaje natural

El usuario debe poder hablar con ORION como lo haría con otra persona.

Los comandos existen únicamente como respaldo.

---

### 💻 Ejecución local

Si una tarea puede ejecutarse localmente, ORION lo hará.

Solo recurrirá a la nube cuando sea necesario.

---

### 🧩 Modularidad

Cada componente puede evolucionar o reemplazarse sin afectar al resto del sistema.

---

### 🔒 Seguridad

La información sensible nunca forma parte del repositorio.

Las claves y configuraciones privadas se almacenan mediante variables de entorno.

---

### 🌎 Multiplataforma

Un único núcleo inteligente.

Adaptadores específicos para:

* Windows
* Linux
* macOS
* Android
* iOS

---

# 🔐 Seguridad

Las claves de acceso nunca deben almacenarse en el repositorio.

Toda la información sensible se gestiona mediante:

```text
.env
```

El repositorio únicamente incluye un archivo de ejemplo:

```text
.env.example
```

---

# 🤝 Contribuciones

Toda sugerencia, mejora o corrección es bienvenida.

Puedes colaborar mediante:

* Reporte de errores.
* Propuestas de nuevas funciones.
* Mejoras en la documentación.
* Pull Requests.

---

# 📄 Licencia

Este proyecto se distribuye bajo la licencia MIT.

---

# 👨‍💻 Autor

**Michel Flores**

Desarrollador de ORION.

Este proyecto nació con la visión de crear un asistente de inteligencia artificial capaz de comprender lenguaje natural, aprender del usuario, automatizar tareas y evolucionar hasta convertirse en un verdadero compañero digital.

---

<div align="center">

## ⭐ Si te gusta ORION, considera apoyar el proyecto dejando una estrella en GitHub.

**Este es solo el comienzo.**

</div>
