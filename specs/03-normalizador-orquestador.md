# Spec 03 — Normalizador y Orquestador

**Responsable:** <nombre> · **Rama:** `feat/orquestador` · **Archivos:** `jeils/orchestrator.py`, `jeils/normalizer.py`

## Contexto y objetivo
Coordinar ambos adaptadores en paralelo y unificar sus resultados en una única `EvaluacionResponse`.

## Actores
API Gateway (invoca), adaptadores SENAMHI y SENACE, dashboard (consume la respuesta).

## Historias de usuario
- H1: Como organizador quiero una sola consulta que me dé clima y antecedentes ambientales juntos.

## Requisitos funcionales
- RF-1: CUANDO llegue una `EvaluacionRequest` válida, EL SISTEMA DEBE invocar ambos adaptadores en paralelo (`asyncio.gather`).
- RF-2: EL SISTEMA DEBE devolver siempre una `EvaluacionResponse` con `es_pronostico = false`.
- RF-3: SI un adaptador falla, ENTONCES EL SISTEMA DEBE devolver respuesta parcial con los datos de la otra fuente y una entrada en `advertencias`.
- RF-4: SI ambos fallan, ENTONCES EL SISTEMA DEBE devolver respuesta con ambas fuentes en `None` y dos advertencias (sin error 500).
- RF-5: EL SISTEMA DEBE reunir en `advertencias` los avisos de cada adaptador (cobertura limitada, sin coincidencias, etc.).
- RF-6: SI la `fecha_evento` es inválida o falta la locación, ENTONCES EL SISTEMA DEBE rechazar la solicitud con error 422 (validación de Pydantic).
- RF-7: EL SISTEMA DEBE aceptar adaptadores inyectables para poder probarse sin internet.

## Requisitos no funcionales
El tiempo total ≈ el del adaptador más lento, no la suma.

## Fuera de alcance
Acceso directo a fuentes externas (es del adaptador).

## Contratos y dependencias
`EvaluacionRequest`, `EvaluacionResponse`, `ResultadoSenamhi`, `ResultadoSenace`.
