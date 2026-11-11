"""Adaptador SENAMHI. Spec: specs/01-adaptador-senamhi.md (Integrante 1).

Flujo: caché -> CKAN package_show (JSON) -> recurso CSV -> filtrar estación -> ResultadoSenamhi.
"""
from datetime import date

from jeils.contracts import Locacion, ResultadoSenamhi


async def consultar(locacion: Locacion, fecha_evento: date) -> ResultadoSenamhi:
    # TODO(integrante 1): implementar según la spec 01.
    raise NotImplementedError("Adaptador SENAMHI pendiente de implementar")
