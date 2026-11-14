"""Servicio de normalización. Spec: specs/03 (Integrante 3).

Une los resultados (o errores) de cada fuente en una EvaluacionResponse.
"""

from jeils.contracts import EvaluacionResponse, ResultadoSenace, ResultadoSenamhi


def _sin_duplicados(avisos: list[str]) -> list[str]:
    """Quita avisos repetidos conservando el orden."""
    return list(dict.fromkeys(a for a in avisos if a))


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
        advertencias.append(
            "Servicio SENACE no disponible temporalmente: validación ambiental pendiente"
        )
    else:
        r_senace = senace
        advertencias += senace.avisos

    return EvaluacionResponse(
        senamhi=r_senamhi,
        senace=r_senace,
        advertencias=_sin_duplicados(advertencias),
        es_pronostico=False,
    )
