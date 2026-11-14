"""Cubre spec 03 (RF-1, RF-3, RF-4, RF-5, RF-7). Sin internet: adaptadores simulados."""

import asyncio
import time
from datetime import date

from jeils.contracts import (
    EvaluacionRequest,
    FuenteNoDisponible,
    Locacion,
    ResultadoSenace,
    ResultadoSenamhi,
)

from jeils.orchestrator import evaluar_locacion

REQ = EvaluacionRequest(
    locacion=Locacion(departamento="Lima"), fecha_evento=date(2026, 12, 20)
)


async def ok_senamhi(loc, fecha):
    return ResultadoSenamhi(avisos=["Estación lejana"])


async def ok_senace(loc):
    return ResultadoSenace(avisos=["Búsqueda por texto, puede ser incompleta"])


async def falla(*args):
    raise FuenteNoDisponible("fuente")


async def lenta(*args):
    await asyncio.sleep(5)


async def test_ambas_fuentes_ok_y_avisos_reunidos():  # RF-1, RF-5
    r = await evaluar_locacion(REQ, ok_senamhi, ok_senace)
    assert r.senamhi is not None and r.senace is not None
    assert r.advertencias == [
        "Estación lejana",
        "Búsqueda por texto, puede ser incompleta",
    ]
    assert r.es_pronostico is False


async def test_respuesta_parcial_si_cae_senace():  # RF-3
    r = await evaluar_locacion(REQ, ok_senamhi, falla)
    assert r.senamhi is not None and r.senace is None
    assert any("SENACE" in a for a in r.advertencias)


async def test_respuesta_parcial_si_cae_senamhi():  # RF-3
    r = await evaluar_locacion(REQ, falla, ok_senace)
    assert r.senamhi is None and r.senace is not None
    assert any("SENAMHI" in a for a in r.advertencias)


async def test_ambas_caen_no_lanza_error():  # RF-4
    r = await evaluar_locacion(REQ, falla, falla)
    assert r.senamhi is None and r.senace is None
    assert len(r.advertencias) == 2


async def test_consulta_en_paralelo():  # RF-1
    async def espera(*args):
        await asyncio.sleep(0.3)
        return ResultadoSenace()

    async def espera_senamhi(*args):
        await asyncio.sleep(0.3)
        return ResultadoSenamhi()

    t0 = time.perf_counter()
    await evaluar_locacion(REQ, espera_senamhi, espera)
    assert time.perf_counter() - t0 < 0.55  # ~0.3 s, no 0.6 s


async def test_fuente_lenta_no_bloquea_a_la_otra():  # robustez
    t0 = time.perf_counter()
    r = await evaluar_locacion(REQ, ok_senamhi, lenta, limite_segundos=0.2)
    assert time.perf_counter() - t0 < 1
    assert r.senamhi is not None and r.senace is None
    assert any("SENACE" in a for a in r.advertencias)
