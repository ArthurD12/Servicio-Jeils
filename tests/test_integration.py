"""Pruebas de integración con DATOS REALES (usan internet).

No corren por defecto ni en el CI. Ejecutar a mano cuando los adaptadores estén integrados:
    pytest -m integration -s
SENACE requiere SENACE_API_KEY en el .env.
"""
from datetime import date

import pytest

from jeils.config import get_settings
from jeils.contracts import EvaluacionRequest, Locacion
from jeils.orchestrator import evaluar_locacion

pytestmark = pytest.mark.integration

REQ = EvaluacionRequest(locacion=Locacion(departamento="LIMA", provincia="LIMA"), fecha_evento=date(2026, 12, 20))


async def test_evaluacion_real_lima():
    r = await evaluar_locacion(REQ)
    print(r.model_dump_json(indent=2))
    assert r.es_pronostico is False
    assert r.senamhi is not None or r.senace is not None  # al menos una fuente real respondió


async def test_senamhi_real_devuelve_clima():
    from jeils.adapters import senamhi

    r = await senamhi.consultar(REQ.locacion, REQ.fecha_evento)
    assert r.estacion is not None or r.avisos  # hay estación o un aviso explicando por qué no


async def test_senace_real_devuelve_proyectos():
    if not get_settings().senace_api_key:
        pytest.skip("Falta SENACE_API_KEY en .env")
    from jeils.adapters import senace

    r = await senace.consultar(REQ.locacion)
    assert r.total >= 0
