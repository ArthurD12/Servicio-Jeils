"""Servicio de normalización. Spec: specs/03 (Integrante 3).

Une los resultados (o errores) de cada fuente en una EvaluacionResponse.
"""
from jeils.contracts import EvaluacionResponse, ResultadoSenace, ResultadoSenamhi


def normalizar(
    senamhi: ResultadoSenamhi | BaseException,
    senace: ResultadoSenace | BaseException,
) -> EvaluacionResponse:
    advertencias: list[str] = []
    r_senamhi = r_senace = None

    if isinstance(senamhi, BaseException):
        advertencias.append("Servicio SENAMHI no disponible temporalmente")
    else:
        r_senamhi = senamhi
        advertencias += senamhi.avisos

    if isinstance(senace, BaseException):
        advertencias.append("Servicio SENACE no disponible temporalmente")
    else:
        r_senace = senace
        advertencias += senace.avisos

    return EvaluacionResponse(senamhi=r_senamhi, senace=r_senace, advertencias=advertencias)
