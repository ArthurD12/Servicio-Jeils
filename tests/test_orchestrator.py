"""Cubre spec 03 (RF-1, RF-3, RF-4, RF-7). Sin internet: adaptadores simulados."""
from jeils.contracts import (
    EvaluacionRequest, FuenteNoDisponible, ResultadoSenace, ResultadoSenamhi,
)
from jeils.orchestrator import evaluar_locacion

REQ = EvaluacionRequest(locacion={"departamento": "Lima"}, fecha_evento="2026-12-20")


async def ok_senamhi(loc, fecha):
    return ResultadoSenamhi(avisos=["Estación lejana"])


async def ok_senace(loc):
    return ResultadoSenace()


async def falla(*args):
    raise FuenteNoDisponible("fuente")


async def test_ambas_fuentes_ok():
    r = await evaluar_locacion(REQ, ok_senamhi, ok_senace)
    assert r.senamhi is not None and r.senace is not None
    assert r.advertencias == ["Estación lejana"]
    assert r.es_pronostico is False


async def test_respuesta_parcial_si_cae_senace():
    r = await evaluar_locacion(REQ, ok_senamhi, falla)
    assert r.senamhi is not None and r.senace is None
    assert any("SENACE" in a for a in r.advertencias)


async def test_ambas_caen_no_lanza_error():
    r = await evaluar_locacion(REQ, falla, falla)
    assert r.senamhi is None and r.senace is None
    assert len(r.advertencias) == 2
