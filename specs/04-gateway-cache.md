# Spec 04 — Gateway y Caché

**Responsable:** <nombre> · **Rama:** `feat/gateway-cache` · **Archivos:** `jeils/gateway.py`, `jeils/cache.py`, `jeils/main.py`

## Contexto y objetivo
Punto único de entrada con controles de acceso (CORS, límite de peticiones, JWT) y caché clave-valor compartida por los adaptadores.

## Actores
Dashboard, orquestador, adaptadores.

## Historias de usuario
- H1: Como equipo queremos un único punto de entrada controlado para proteger el backend.
- H2: Como adaptador quiero guardar y recuperar respuestas procesadas para evitar descargas repetidas.

## Requisitos funcionales
- RF-1: EL SISTEMA DEBE exponer `POST /api/v1/evaluacion` y `GET /health`.
- RF-2: EL SISTEMA DEBE habilitar CORS solo para los orígenes configurados.
- RF-3: SI un cliente excede el límite de peticiones (p. ej. 30/min por IP), ENTONCES EL SISTEMA DEBE responder 429.
- RF-4: SI la solicitud no trae un JWT válido, ENTONCES EL SISTEMA DEBE responder 401. (Puede activarse por configuración durante el desarrollo.)
- RF-5: EL SISTEMA DEBE ofrecer `cache.get(clave)` y `cache.set(clave, valor, ttl)` con valores JSON.
- RF-6: CUANDO `REDIS_URL` esté definido, EL SISTEMA DEBE usar Redis; si no, caché en memoria con TTL.
- RF-7: SI Redis no está disponible, ENTONCES EL SISTEMA DEBE degradar a caché en memoria y registrar el error.
- RF-8: EL SISTEMA DEBE permitir leer una entrada vencida como "última copia válida" (`get_stale`) para contingencia.

## Requisitos no funcionales
Los límites y orígenes salen de configuración, no de constantes en el código.

## Fuera de alcance
Gestión de usuarios (el JWT puede ser de prueba).

## Contratos y dependencias
Usa `EvaluacionRequest`/`EvaluacionResponse` en el endpoint; `Settings` de `config.py`.
