"""Orquestador Core. Spec: specs/03 (Integrante 3)."""
import asyncio
import logging

from jeils.adapters import senace, senamhi
from jeils.contracts import EvaluacionRequest, EvaluacionResponse
from jeils.normalizer import normalizar

log = logging.getLogger(__name__)


async def evaluar_locacion(
    req: EvaluacionRequest,
    consultar_senamhi=senamhi.consultar,
    consultar_senace=senace.consultar,
) -> EvaluacionResponse:
    """Llama a ambos adaptadores en paralelo; una fuente caída no cancela la otra."""
    r_senamhi, r_senace = await asyncio.gather(
        consultar_senamhi(req.locacion, req.fecha_evento),
        consultar_senace(req.locacion),
        return_exceptions=True,
    )
    for nombre, r in (("SENAMHI", r_senamhi), ("SENACE", r_senace)):
        if isinstance(r, BaseException):
            log.warning("Fuente %s falló: %r", nombre, r)
    return normalizar(r_senamhi, r_senace)
