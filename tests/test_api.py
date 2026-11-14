"""Pruebas de la API. Sin internet: los adaptadores se simulan con monkeypatch."""
import pytest
from fastapi.testclient import TestClient

from jeils.contracts import ResultadoSenace, ResultadoSenamhi
from jeils.main import app

client = TestClient(app)
BODY = {"locacion": {"departamento": "Lima"}, "fecha_evento": "2026-12-20"}


@pytest.fixture
def adaptadores_simulados(monkeypatch):
    async def fake_senamhi(locacion, fecha_evento):
        return ResultadoSenamhi(avisos=["Dato de prueba"])

    async def fake_senace(locacion):
        return ResultadoSenace()

    monkeypatch.setattr("jeils.adapters.senamhi.consultar", fake_senamhi)
    monkeypatch.setattr("jeils.adapters.senace.consultar", fake_senace)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_evaluacion_valida_con_adaptadores_simulados(adaptadores_simulados):
    r = client.post("/api/v1/evaluacion", json=BODY)
    assert r.status_code == 200
    j = r.json()
    assert j["es_pronostico"] is False
    assert j["senamhi"] is not None and j["senace"] is not None
    assert j["advertencias"] == ["Dato de prueba"]


def test_evaluacion_degrada_si_cae_una_fuente(monkeypatch):
    async def cae(*args):
        raise RuntimeError("fuente caída")

    async def ok_senace(locacion):
        return ResultadoSenace()

    monkeypatch.setattr("jeils.adapters.senamhi.consultar", cae)
    monkeypatch.setattr("jeils.adapters.senace.consultar", ok_senace)
    r = client.post("/api/v1/evaluacion", json=BODY)
    assert r.status_code == 200
    assert r.json()["senamhi"] is None
    assert any("SENAMHI" in a for a in r.json()["advertencias"])


def test_evaluacion_invalida_422():
    r = client.post("/api/v1/evaluacion", json={"locacion": {}, "fecha_evento": "2026-12-20"})
    assert r.status_code == 422
