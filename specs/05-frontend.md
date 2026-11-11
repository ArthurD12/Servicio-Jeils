# Spec 05 — Frontend (Dashboard)

**Responsable:** <nombre> · **Rama:** `feat/frontend` · **Carpeta:** `frontend/`

## Contexto y objetivo
Una o dos ventanas web donde el organizador indica locación y fecha y ve clima histórico y antecedentes ambientales.

## Actores
Organizador de eventos de Jeils.

## Historias de usuario
- H1: Como organizador quiero ingresar departamento, provincia, distrito (o ubigeo) y la fecha para evaluar una locación.
- H2: Como organizador quiero ver claramente qué datos son históricos y cuáles faltan.

## Requisitos funcionales
- RF-1: CUANDO el usuario envíe el formulario con locación y fecha, EL SISTEMA DEBE llamar a `POST /api/v1/evaluacion` y mostrar el resultado.
- RF-2: EL SISTEMA DEBE mostrar temperatura, humedad, precipitación y la estación usada (con su distancia).
- RF-3: EL SISTEMA DEBE mostrar los proyectos de SENACE (título, titular, estado, fecha).
- RF-4: EL SISTEMA DEBE mostrar siempre la leyenda "Datos históricos; no constituyen un pronóstico".
- RF-5: SI la respuesta trae `advertencias`, ENTONCES EL SISTEMA DEBE mostrarlas de forma visible (p. ej. "validación ambiental pendiente").
- RF-6: MIENTRAS se espera la respuesta, EL SISTEMA DEBE mostrar un indicador de carga.
- RF-7: SI la llamada falla, ENTONCES EL SISTEMA DEBE mostrar un mensaje claro sin romper la página.
- RF-8: EL SISTEMA NO DEBE contener ninguna API Key.

## Requisitos no funcionales
HTML + JS sin framework; usable en móvil; textos en español.

## Fuera de alcance
Autenticación de usuarios; mapas (mejora opcional con Leaflet).

## Contratos y dependencias
Consume `EvaluacionResponse` (ver `jeils/contracts.py`).
