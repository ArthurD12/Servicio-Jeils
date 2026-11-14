"""Cubre spec 03 (RF-2, RF-3, RF-5)."""

from jeils.contracts import FuenteNoDisponible, ResultadoSenace, ResultadoSenamhi
from jeils.normalizer import normalizar


def test_siempre_historico():  # RF-2
    r = normalizar(ResultadoSenamhi(), ResultadoSenace())
    assert r.es_pronostico is False


def test_avisos_sin_duplicados():  # RF-5
    r = normalizar(
        ResultadoSenamhi(avisos=["A", "B"]), ResultadoSenace(avisos=["B", "C"])
    )
    assert r.advertencias == ["A", "B", "C"]


def test_error_se_convierte_en_advertencia():  # RF-3
    r = normalizar(FuenteNoDisponible("SENAMHI"), ResultadoSenace())
    assert r.senamhi is None and r.senace is not None
    assert r.advertencias == ["Servicio SENAMHI no disponible temporalmente"]


def test_senace_caido_marca_validacion_pendiente():  # RF-3
    r = normalizar(ResultadoSenamhi(), RuntimeError("boom"))
    assert "validación ambiental pendiente" in r.advertencias[0]
