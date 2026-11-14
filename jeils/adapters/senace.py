"""Adaptador SENACE. Spec: specs/02-adaptador-senace.md (Integrante 2).

Flujo: caché -> GET CarteraProyectos?auth_key=... (JSON) -> filtrar por texto -> ResultadoSenace.

Notas importantes (ver docs/constitution.md):
- La API de SENACE NO trae coordenadas: la coincidencia con la locación es por texto.
- Los resultados son referenciales; no autorizan el uso de un terreno.
"""
import asyncio
import logging
import re
import unicodedata
from datetime import date, datetime

import httpx

from jeils.cache import get_cache
from jeils.config import get_settings
from jeils.contracts import (
    FuenteNoDisponible,
    Locacion,
    ProyectoAmbiental,
    ResultadoSenace,
)

log = logging.getLogger(__name__)

FUENTE = "SENACE"
CLAVE_CACHE = "senace:cartera_proyectos"  # la lista completa no depende de la locación


# ---------------------------------------------------------------------------
# Utilidades de texto y fechas
# ---------------------------------------------------------------------------
def _limpiar(texto: str | None) -> str:
    """Minúsculas y sin tildes: 'Pátivilca' -> 'pativilca'. RF-5."""
    if not texto:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return sin_tildes.lower().strip()


def _convertir_fecha(texto: str | None) -> date | None:
    """Convierte 'DD/MM/AAAA' a date. Si no se puede, devuelve None. RF-8."""
    if not texto:
        return None
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _terminos_de_busqueda(locacion: Locacion) -> list[str]:
    """Distrito, provincia y departamento (los que existan), ya limpios."""
    terminos = [
        _limpiar(locacion.distrito),
        _limpiar(locacion.provincia),
        _limpiar(locacion.departamento),
    ]
    return [t for t in terminos if t]


def _coincide(registro: dict, terminos: list[str]) -> bool:
    """True si algún término aparece como palabra completa en título o unidad. RF-5."""
    texto = _limpiar(f"{registro.get('TITULO_PROYECTO') or ''} {registro.get('UNIDAD_PROYECTO') or ''}")
    for termino in terminos:
        # \b evita que 'lima' coincida con 'limache'
        if re.search(rf"\b{re.escape(termino)}\b", texto):
            return True
    return False


def _a_proyecto(registro: dict) -> ProyectoAmbiental | None:
    """Convierte un registro de SENACE a ProyectoAmbiental. Si no tiene ID válido, se descarta."""
    try:
        return ProyectoAmbiental(
            id=int(registro["ID"]),
            titular=registro.get("TITULAR"),
            ruc=None if registro.get("RUC") is None else str(registro["RUC"]),
            titulo_proyecto=registro.get("TITULO_PROYECTO"),
            unidad_proyecto=registro.get("UNIDAD_PROYECTO"),
            tipo=registro.get("TIPO"),
            actividad=registro.get("ACTIVIDAD"),
            fecha_inicio=_convertir_fecha(registro.get("FECHA_INICIO")),
            estado=registro.get("ESTADO"),
        )
    except (KeyError, TypeError, ValueError):
        log.warning("Registro SENACE descartado por tener un ID inválido")
        return None


# ---------------------------------------------------------------------------
# Llamada a la API de SENACE
# ---------------------------------------------------------------------------
async def _descargar_cartera() -> list[dict]:
    """Llama a SENACE. Timeout y reintentos con backoff exponencial (constitución §5).

    Lanza FuenteNoDisponible si no se pudo obtener una lista válida. RF-2, RF-4, RF-7.
    """
    ajustes = get_settings()
    if not ajustes.senace_api_key:
        raise FuenteNoDisponible(FUENTE, "La API Key no está configurada (SENACE_API_KEY).")

    intentos = ajustes.http_max_retries + 1
    ultimo_error = ""
    for intento in range(intentos):
        try:
            async with httpx.AsyncClient(timeout=ajustes.http_timeout_seconds) as cliente:
                # La API Key va en el parámetro auth_key y viene de la configuración. RF-2
                respuesta = await cliente.get(
                    ajustes.senace_url, params={"auth_key": ajustes.senace_api_key}
                )
            if respuesta.status_code in (401, 403):
                # Clave inválida: reintentar no sirve de nada
                raise FuenteNoDisponible(FUENTE, f"API Key rechazada (HTTP {respuesta.status_code}).")
            if respuesta.status_code != 200:  # RF-4
                ultimo_error = f"HTTP {respuesta.status_code}"
            else:
                datos = respuesta.json()
                if isinstance(datos, list):  # RF-4
                    return datos
                ultimo_error = "La respuesta no es una lista JSON"
        except FuenteNoDisponible:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            # ValueError cubre un JSON mal formado
            ultimo_error = type(exc).__name__
        log.warning("SENACE intento %s/%s falló: %s", intento + 1, intentos, ultimo_error)
        if intento < intentos - 1:
            await asyncio.sleep(0.5 * 2**intento)  # 0.5 s, 1 s, ...
    raise FuenteNoDisponible(FUENTE, ultimo_error)


async def _obtener_cartera() -> tuple[list[dict], list[str]]:
    """Devuelve (registros, avisos). Orden: caché vigente -> API -> caché vencida -> error."""
    cache = get_cache()

    vigente = await cache.get(CLAVE_CACHE)
    if vigente is not None:  # RF-3: no se llama a SENACE
        return vigente, []

    try:
        registros = await _descargar_cartera()
    except FuenteNoDisponible:
        copia = await cache.get_stale(CLAVE_CACHE)  # RF-7
        if copia is not None:
            return copia, ["SENACE no respondió: se muestran datos guardados anteriormente."]
        raise

    await cache.set(CLAVE_CACHE, registros)
    return registros, []


# ---------------------------------------------------------------------------
# Punto de entrada que usa el Orquestador
# ---------------------------------------------------------------------------
async def consultar(locacion: Locacion) -> ResultadoSenace:
    """Devuelve los proyectos de SENACE cuyo título/unidad mencionan la locación. RF-1."""
    registros, avisos = await _obtener_cartera()

    terminos = _terminos_de_busqueda(locacion)
    proyectos: list[ProyectoAmbiental] = []
    if terminos:
        for registro in registros:
            if isinstance(registro, dict) and _coincide(registro, terminos):
                proyecto = _a_proyecto(registro)
                if proyecto is not None:
                    proyectos.append(proyecto)
        # Los más recientes primero; los que no tienen fecha, al final
        proyectos.sort(key=lambda p: p.fecha_inicio or date.min, reverse=True)

    if not proyectos:  # RF-6
        avisos.append(
            "No se encontraron proyectos de SENACE para esta locación. La búsqueda es por "
            "texto (SENACE no entrega coordenadas) y puede ser incompleta."
        )

    return ResultadoSenace(proyectos=proyectos, total=len(proyectos), avisos=avisos)
