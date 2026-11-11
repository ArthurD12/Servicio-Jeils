from fastapi.testclient import TestClient

from jeils.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_evaluacion_valida_degrada_con_adaptadores_pendientes():
    r = client.post("/api/v1/evaluacion", json={"locacion": {"departamento": "Lima"}, "fecha_evento": "2026-12-20"})
    assert r.status_code == 200
    assert r.json()["es_pronostico"] is False


def test_evaluacion_invalida_422():
    r = client.post("/api/v1/evaluacion", json={"locacion": {}, "fecha_evento": "2026-12-20"})
    assert r.status_code == 422
