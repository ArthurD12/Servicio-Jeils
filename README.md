# Servicio-Jeils

Integración de servicios web (SENAMHI + SENACE) para la validación logística y ambiental de locaciones en la planificación de eventos. Curso: Arquitectura Orientada al Servicio.

> Los datos de SENAMHI son **históricos, no un pronóstico**. Los de SENACE son **referenciales**, no una autorización de uso del terreno.

## Cómo trabajamos (SDD: Spec-Driven Development)
1. Las reglas globales están en [`docs/constitution.md`](docs/constitution.md) y los contratos de datos en [`jeils/contracts.py`](jeils/contracts.py).
2. Cada módulo tiene su spec en [`specs/`](specs/) con requisitos EARS. La IA implementa **a partir de la spec**.
3. Cada requisito (RF) debe tener un test. Se trabaja en una rama por módulo y se integra con Pull Request revisado por otro integrante.
4. Cada integrante registra sus prompts en [`docs/prompts.md`](docs/prompts.md).

Cualquier IA (OpenCode, Claude Code, Cursor, Copilot...) debe seguir [`AGENTS.md`](AGENTS.md).

## Reparto de módulos
| # | Módulo | Spec | Archivos | Responsable |
|---|---|---|---|---|
| 1 | Adaptador SENAMHI | [01](specs/01-adaptador-senamhi.md) | `jeils/adapters/senamhi.py` | CARHUATANTA VÉLEZ Luis Joaquín |
| 2 | Adaptador SENACE | [02](specs/02-adaptador-senace.md) | `jeils/adapters/senace.py` | MENÉNDEZ REINOSO Oscar Sebastian |
| 3 | Normalizador + Orquestador | [03](specs/03-normalizador-orquestador.md) | `jeils/normalizer.py`, `jeils/orchestrator.py` | CANAZA HUAYTA Harold Jhampier |
| 4 | Gateway + Caché | [04](specs/04-gateway-cache.md) | `jeils/gateway.py`, `jeils/cache.py` | LLOCLLA CASTILLO Bella Maria Adelaida |
| 5 | Frontend | [05](specs/05-frontend.md) | `frontend/` | BRAÑEZ REYNOSO Delvis Damian |

## Arquitectura
```
Dashboard -> API Gateway -> Orquestador -> [Adaptador SENAMHI | Adaptador SENACE] -> Normalizador -> respuesta
                                                   |  caché (Redis / memoria)  |
                                           CKAN SENAMHI (JSON+CSV)     API SENACE (JSON, API Key)
```

## Puesta en marcha
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env             # Windows: copy .env.example .env  (y completar SENACE_API_KEY)
pytest
uvicorn jeils.main:app --reload  # http://localhost:8000  ·  docs: /docs
```
Con Docker (incluye Redis): `docker compose up --build`.

## Equipo
CANAZA HUAYTA Harold Jhampier · LLOCLLA CASTILLO Bella Maria Adelaida · MENÉNDEZ REINOSO Oscar Sebastian · BRAÑEZ REYNOSO Delvis Damian · CARHUATANTA VÉLEZ Luis Joaquín
