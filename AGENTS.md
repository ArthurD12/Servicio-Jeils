# AGENTS.md — Reglas para cualquier IA o agente en este repo

Proyecto: **Jeils**, evaluación logística y ambiental de locaciones para eventos
(SENAMHI = clima histórico, SENACE = antecedentes ambientales). Idioma: español.

## Antes de escribir código (en este orden)
1. Lee `docs/constitution.md` (reglas globales: no se repiten en las specs).
2. Lee `jeils/contracts.py` (contratos de datos compartidos).
3. Lee la spec de TU módulo en `specs/` y cumple sus requisitos EARS.

## Reglas
- Toca **solo** los archivos del módulo asignado (ver tabla en `README.md`).
- **No modifiques `jeils/contracts.py`** sin acuerdo del equipo (cambio solo vía Pull Request revisado).
- Cada requisito RF-n de la spec debe tener al menos un test en `tests/`.
- Nunca escribas claves, tokens ni la API Key de SENACE en el código ni en commits. Usa variables de entorno (`.env`, ver `.env.example`).
- No inventes endpoints ni campos: usa los de la spec y del entregable.
- Los datos de SENAMHI son **históricos**, nunca los presentes como pronóstico.
- No repitas en las specs lo que ya está en la constitución; refiérete a ella.
- Si algo es ambiguo, pregunta o deja un `TODO(pregunta)`; no adivines.

## Comandos
- Instalar: `pip install -e ".[dev]"`
- Tests: `pytest`
- Ejecutar API: `uvicorn jeils.main:app --reload` (docs en http://localhost:8000/docs)
- Redis local (opcional): `docker compose up redis`

## Git
- Una rama por funcionalidad: `feat/<modulo>-<tema>`. Nunca commitear directo a `main`.
- Commits pequeños, en español, formato `tipo(modulo): descripcion` (ej. `feat(senamhi): filtra estación más cercana`).
- Commit con la identidad de la persona que guía a la IA (no cambies `user.name`/`user.email`).
- Abre Pull Request; otro integrante lo revisa antes del merge.
