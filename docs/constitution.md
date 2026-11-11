# Constitución del proyecto Jeils

Reglas globales. Las specs de `specs/` no las repiten: las referencian.

## 1. Propósito y límites
Dashboard que, dada una locación y una fecha de evento, muestra (a) clima **histórico** de
SENAMHI y (b) antecedentes ambientales de SENACE. Es información de apoyo:
- Los datos de SENAMHI **no son un pronóstico**. La respuesta siempre incluye `es_pronostico = false`.
- Los datos de SENACE **no son una autorización de uso del terreno**.
- Si la estación más cercana es lejana, se informa con un aviso (no se oculta).

## 2. Stack
Python 3.11+, FastAPI, Pydantic v2, httpx (async), pandas, Redis (opcional: si `REDIS_URL` está vacío se usa caché en memoria),
pytest, Docker Compose, GitHub Actions. Frontend: HTML + JavaScript sin framework.

## 3. Arquitectura (monolito modular, un módulo por pieza SOA)
| Pieza del entregable | Módulo |
|---|---|
| Dashboard | `frontend/` |
| API Gateway | `jeils/gateway.py` |
| Orquestador Core | `jeils/orchestrator.py` |
| Servicio de normalización | `jeils/normalizer.py` |
| Adaptador SENAMHI | `jeils/adapters/senamhi.py` |
| Adaptador SENACE | `jeils/adapters/senace.py` |
| Caché Redis | `jeils/cache.py` |
| Contratos (DTOs) | `jeils/contracts.py` |

Los módulos solo se comunican mediante los modelos de `contracts.py`. Un adaptador nunca importa a otro.
Cada módulo debe poder extraerse luego a un servicio separado sin cambiar su interfaz.

## 4. Fuentes externas
- **SENAMHI:** CKAN `package_show` (JSON) → recurso CSV (~48 MB, `Content-Type: application/octet-stream`).
  Columnas: ID, ESTACION, FECHA, HORA, LONGITUD, LATITUD, ALTITUD, TEMP, HR, PP, RED, DEPARTAMENTO, PROVINCIA, DISTRITO, UBIGEO.
  Sin autenticación. El CSV no se descarga en cada consulta: se cachea/procesa y se reutiliza.
- **SENACE:** `GET .../Api/datastreams/CarteraProyectos?auth_key={API_KEY}` → JSON (arreglo de objetos).
  Campos: ID, TITULAR, RUC, TITULO_PROYECTO, UNIDAD_PROYECTO, TIPO, ACTIVIDAD, FECHA_INICIO (DD/MM/AAAA), ESTADO.
  No trae coordenadas: la coincidencia con la locación es por texto.

## 5. Errores y resiliencia
- Timeout de 3.5 s por llamada externa, máximo 2 reintentos con backoff exponencial.
- Ante fallo: servir la última copia válida de la caché; si no hay, devolver respuesta parcial con `advertencias`.
- Una fuente caída **nunca** cancela toda la evaluación (degradación gradual).
- Los errores se registran con `logging` (sin datos sensibles).

## 6. Seguridad
- La API Key de SENACE vive solo en el backend (`.env`). Jamás en el frontend ni en git.
- El gateway aplica CORS y límite de peticiones; JWT según la spec 04.

## 7. Calidad
- Cada RF de cada spec tiene al menos un test. Los tests no llaman a internet (se simulan las fuentes).
- Código y comentarios en español; nombres de funciones/variables en español o inglés, pero consistentes.

## 8. Git y participación
- Sin commits directos a `main`; Pull Request con revisión de otro integrante.
- Commits `tipo(modulo): descripcion`, cada persona con su propia identidad.
- Prompts relevantes se registran en `docs/prompts.md`.

## 9. Definición de terminado (por módulo)
Spec cumplida · tests en verde · sin secretos · PR revisado y aprobado.
