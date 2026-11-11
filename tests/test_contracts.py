import pytest
from pydantic import ValidationError

from jeils.contracts import EvaluacionRequest, EvaluacionResponse, Locacion


def test_locacion_requiere_alguna_referencia():
    with pytest.raises(ValidationError):
        Locacion()


def test_request_valido():
    r = EvaluacionRequest(locacion={"departamento": "Lima"}, fecha_evento="2026-12-20")
    assert r.locacion.departamento == "Lima"


def test_respuesta_nunca_es_pronostico_por_defecto():
    assert EvaluacionResponse().es_pronostico is False
