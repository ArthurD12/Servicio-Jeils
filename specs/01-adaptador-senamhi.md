# Spec 01 — Adaptador SENAMHI

**Responsable:** <nombre> · **Rama:** `feat/senamhi` · **Archivo:** `jeils/adapters/senamhi.py`

## Contexto y objetivo
Obtener el clima histórico (temperatura, humedad, precipitación) de la estación SENAMHI más cercana a una locación y entregarlo como `ResultadoSenamhi`.

## Actores
Orquestador Core (lo invoca), caché (`cache.py`), API CKAN de SENAMHI.

## Historias de usuario
- H1: Como organizador quiero ver el clima histórico de la zona para estimar condiciones típicas en la fecha de mi evento.

## Requisitos funcionales
- RF-1: CUANDO el orquestador solicite datos de una locación, EL SISTEMA DEBE devolver un `ResultadoSenamhi` con la estación más cercana y promedios de TEMP, HR y PP.
- RF-2: CUANDO exista una respuesta vigente en caché para la locación, EL SISTEMA NO DEBE consultar CKAN ni descargar el CSV.
- RF-3: CUANDO no haya caché, EL SISTEMA DEBE consultar `package_show`, localizar el recurso CSV y procesarlo (fechas, números, valores faltantes).
- RF-4: EL SISTEMA DEBE usar la `fecha_evento` solo para filtrar registros de periodos similares (mismo mes de años anteriores) si existen datos.
- RF-5: SI la estación más cercana está a más de 100 km (valor configurable), ENTONCES EL SISTEMA DEBE agregar un aviso de cobertura limitada.
- RF-6: SI no hay registros para la locación o periodo, ENTONCES EL SISTEMA DEBE devolver `clima = None` con un aviso, sin lanzar error.
- RF-7: SI la fuente no responde (timeout o error HTTP), ENTONCES EL SISTEMA DEBE usar la última copia de caché; si no existe, lanzar `FuenteNoDisponible`.
- RF-8: EL SISTEMA DEBE aceptar el CSV aunque llegue como `application/octet-stream`.

## Requisitos no funcionales
Timeout, reintentos y caché según constitución §5. El CSV (~48 MB) no se procesa en cada petición.

## Fuera de alcance
Pronóstico. Cualquier otra fuente de clima.

## Contratos y dependencias
Usa `Locacion`, `Estacion`, `ClimaHistorico`, `ResultadoSenamhi`, `FuenteNoDisponible`; usa `cache.py`.
