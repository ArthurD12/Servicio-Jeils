"""Adaptador SENACE. Spec: specs/02-adaptador-senace.md (Integrante 2).

Flujo: caché -> GET CarteraProyectos?auth_key=... (JSON) -> filtrar por texto -> ResultadoSenace.
"""
from jeils.contracts import Locacion, ResultadoSenace


async def consultar(locacion: Locacion) -> ResultadoSenace:
    # TODO(integrante 2): implementar según la spec 02.
    raise NotImplementedError("Adaptador SENACE pendiente de implementar")
