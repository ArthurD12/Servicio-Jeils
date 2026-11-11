"""Caché clave-valor (JSON). Redis si REDIS_URL está definido; si no, memoria.

Módulo del Integrante 4 (spec 04). Interfaz usada por los adaptadores.
"""
import json
import logging
import time
from typing import Any

from jeils.config import get_settings

log = logging.getLogger(__name__)


class MemoryCache:
    def __init__(self):
        self._data: dict[str, tuple[float, str]] = {}  # clave -> (expira_en, json)

    async def get(self, clave: str) -> Any | None:
        item = self._data.get(clave)
        if item and item[0] > time.time():
            return json.loads(item[1])
        return None

    async def get_stale(self, clave: str) -> Any | None:
        """Devuelve el valor aunque haya vencido (copia de contingencia)."""
        item = self._data.get(clave)
        return json.loads(item[1]) if item else None

    async def set(self, clave: str, valor: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else get_settings().cache_ttl_seconds
        self._data[clave] = (time.time() + ttl, json.dumps(valor, default=str))


class RedisCache:
    """TODO(integrante 4): completar get_stale con una segunda clave `<clave>:stale` sin TTL."""

    def __init__(self, url: str):
        import redis.asyncio as redis

        self._r = redis.from_url(url, decode_responses=True)

    async def get(self, clave: str) -> Any | None:
        raw = await self._r.get(clave)
        return json.loads(raw) if raw else None

    async def get_stale(self, clave: str) -> Any | None:
        raw = await self._r.get(f"{clave}:stale")
        return json.loads(raw) if raw else None

    async def set(self, clave: str, valor: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else get_settings().cache_ttl_seconds
        raw = json.dumps(valor, default=str)
        await self._r.set(clave, raw, ex=ttl)
        await self._r.set(f"{clave}:stale", raw)


_cache = None


def get_cache():
    global _cache
    if _cache is None:
        url = get_settings().redis_url
        try:
            _cache = RedisCache(url) if url else MemoryCache()
        except Exception:  # noqa: BLE001
            log.exception("Redis no disponible; usando caché en memoria")
            _cache = MemoryCache()
    return _cache
