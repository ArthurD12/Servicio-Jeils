# Spec 02 — Adaptador SENACE

**Responsable:** <nombre> · **Rama:** `feat/senace` · **Archivo:** `jeils/adapters/senace.py`

## Contexto y objetivo
Consultar la Cartera de Proyectos de SENACE y devolver antecedentes ambientales relacionados con la locación como `ResultadoSenace`.

## Actores
Orquestador Core, caché, API de datos abiertos de SENACE.

## Historias de usuario
- H1: Como organizador quiero ver proyectos y certificaciones ambientales de la zona para conocer antecedentes antes de planificar.

## Requisitos funcionales
- RF-1: CUANDO el orquestador solicite antecedentes de una locación, EL SISTEMA DEBE devolver un `ResultadoSenace` con los proyectos coincidentes.
- RF-2: EL SISTEMA DEBE enviar la API Key en el parámetro `auth_key`, leída de la configuración (nunca fija en código).
- RF-3: CUANDO exista respuesta vigente en caché, EL SISTEMA NO DEBE llamar a SENACE.
- RF-4: EL SISTEMA DEBE verificar HTTP 200 y que el JSON sea una lista antes de procesar.
- RF-5: EL SISTEMA DEBE filtrar por coincidencia de texto entre la locación (distrito, provincia, departamento) y `TITULO_PROYECTO`/`UNIDAD_PROYECTO`, ignorando mayúsculas y tildes.
- RF-6: SI no hay coincidencias, ENTONCES EL SISTEMA DEBE devolver `proyectos = []` con un aviso de que la búsqueda es por texto y puede ser incompleta.
- RF-7: SI SENACE no responde o la API Key es inválida (401/403), ENTONCES EL SISTEMA DEBE usar caché si existe; si no, lanzar `FuenteNoDisponible`.
- RF-8: EL SISTEMA DEBE convertir `FECHA_INICIO` (DD/MM/AAAA) a `date`.

## Requisitos no funcionales
Constitución §5 y §6. La respuesta (~1.4 MB) se cachea.

## Fuera de alcance
Determinar si un terreno está autorizado.

## Contratos y dependencias
Usa `Locacion`, `ProyectoAmbiental`, `ResultadoSenace`, `FuenteNoDisponible`; usa `cache.py`.
