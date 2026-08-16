# Skills en ORION

Una Skill describe una capacidad especializada de ORION de forma legible tanto
para el código como, en el futuro, para un modelo de IA. La Fase 1 introduce el
formato y el registro; la ejecución de Tools, el agente y la selección por LLM
quedan para fases posteriores.

## Qué es una Skill

Una Skill contiene:

- `name`: nombre único (coincide con el directorio de la Skill).
- `description`: descripción breve de la capacidad.
- `instructions`: cuerpo de `SKILL.md` con instrucciones detalladas.
- `metadata`: secciones estructuradas (`cuando_utilizar`,
  `herramientas_relacionadas`, `reglas`) y la ruta de origen.

## Diferencia entre Skill y Tool

- Una **Skill** describe *qué capacidad existe*, cuándo debe usarse y con qué
  reglas. Es declarativa y no ejecuta nada.
- Una **Tool** será (en fases posteriores) una acción ejecutable que ORION podrá
  invocar (abrir una aplicación, buscar en la web, etc.).

## Estructura

```
core/skills/
    contratos.py       # Skill y SkillNoEncontrada
    lector.py          # parsea SKILL.md
    registro.py        # SkillRegistry y helpers de módulo
    <nombre>/SKILL.md  # definición de cada Skill
```

## Cómo crear una nueva Skill

1. Crea un directorio en `core/skills/<nombre>/`.
2. Crea su `SKILL.md` con front-matter (`nombre`, `descripcion`) y las
   secciones `## Cuándo utilizar`, `## Herramientas relacionadas` y `## Reglas`.

Ejemplo:

```markdown
---
nombre: ejemplo
descripcion: Descripción breve de la capacidad.
---

# Ejemplo

## Cuándo utilizar
- cuando ...

## Herramientas relacionadas
- herramienta_ejemplo

## Reglas
- regla importante
```

3. El registro la detecta automáticamente al descubrir.

## Cómo descubrir una Skill

```python
from core.skills import SkillRegistry, obtener_skill, skills_disponibles

registro = SkillRegistry()
registro.descubrir()          # escanea core/skills y devuelve las Skills
registro.listar()             # lista las Skills conocidas
registro.nombres()            # ["aplicaciones", "archivos", "navegador", "sistema"]
registro.obtener("navegador") # Skill | lanza SkillNoEncontrada

skills_disponibles()          # helpers de módulo sobre el registro por defecto
obtener_skill("sistema")
```

ORION también responde consultas en lenguaje natural como "lista skills" o
"que skills tienes".

## Fuera de esta fase

- Ejecución de Tools.
- Agente autónomo, planificación y razonamiento ReAct.
- Selección de Skills mediante LLM.
- Permisos avanzados y ejecución arbitraria de comandos.
- Instalación dinámica de Skills y sistema de plugins.