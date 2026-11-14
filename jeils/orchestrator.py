"""Orquestador Core. Spec: specs/03-normalizador-orquestador.md (Integrante 3)."""
import asyncio
import logging

from jeils.adapters import senace, senamhi
from jeils.config import get_settings
from jeils.contracts import EvaluacionRequest, EvaluacionResponse, FuenteNoDisponible
from jeils.normalizer import normalizar

log = logging.getLogger(__name__)

# Margen sobre el timeout HTTP: el adaptador puede reintentar (constitución §5).
_FACTOR_ESPERA = 3


async def _con_limite(nombre: str, coro, limite: float):
    """Ejecuta la consulta de una fuente con un tiempo máximo total."""
    try:
        return await asyncio.wait_for(coro, timeout=limite)
    except asyncio.TimeoutError as exc:
        raise FuenteNoDisponible(nombre, "tiempo de espera agotado") from exc


async def evaluar_locacion(
    req: EvaluacionRequest,
    consultar_senamhi=None,
    consultar_senace=None,
    limite_segundos: float | None = None,
) -> EvaluacionResponse:
    """Llama a ambos adaptadores en paralelo; una fuente caída no cancela la otra (RF-1, RF-3, RF-4)."""
    # Se resuelven al momento de la llamada (no al importar) para poder simularlos en pruebas.
    consultar_senamhi = consultar_senamhi or senamhi.consultar
    consultar_senace = consultar_senace or senace.consultar
    limite = limite_segundos or get_settings().http_timeout_seconds * _FACTOR_ESPERA
    r_senamhi, r_senace = await asyncio.gather(
        _con_limite("SENAMHI", consultar_senamhi(req.locacion, req.fecha_evento), limite),
        _con_limite("SENACE", consultar_senace(req.locacion), limite),
        return_exceptions=True,
    )
    for nombre, r in (("SENAMHI", r_senamhi), ("SENACE", r_senace)):
        if isinstance(r, BaseException):
            log.warning("Fuente %s falló: %r", nombre, r)
    return normalizar(r_senamhi, r_senace)
