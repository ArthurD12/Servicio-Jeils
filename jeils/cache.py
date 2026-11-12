
"""Caché JSON con Redis y respaldo en memoria.

Módulo del Integrante 4: Gateway + Caché.
"""

import json
import logging
import time
from typing import Any

from redis.exceptions import RedisError

from jeils.config import get_settings

log = logging.getLogger(__name__)


class MemoryCache:
    """Almacena datos temporalmente en memoria."""

    def __init__(self):
        self._data: dict[str, tuple[float, str]] = {}

    async def get(self, clave: str) -> Any | None:
        item = self._data.get(clave)

        if item and item[0] > time.time():
            return json.loads(item[1])

        return None

    async def get_stale(self, clave: str) -> Any | None:
        """Recupera datos incluso cuando su TTL haya vencido."""
        item = self._data.get(clave)
        return json.loads(item[1]) if item else None

    async def set(
        self, clave: str, valor: Any, ttl: int | None = None
    ) -> None:
        if ttl is None:
            ttl = get_settings().cache_ttl_seconds

        self._data[clave] = (
            time.time() + ttl,
            json.dumps(valor, default=str),
        )


class RedisCache:
    """Utiliza Redis y mantiene un respaldo local en memoria."""

    def __init__(self, url: str):
        import redis.asyncio as redis

        self._r = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        self._memory = MemoryCache()
        self._redis_disponible = True

    def _registrar_fallo(self):
        if self._redis_disponible:
            log.exception(
                "Redis no disponible; usando caché en memoria"
            )
        self._redis_disponible = False

    async def get(self, clave: str) -> Any | None:
        if self._redis_disponible:
            try:
                raw = await self._r.get(clave)
                if raw is not None:
                    return json.loads(raw)
            except RedisError:
                self._registrar_fallo()

        return await self._memory.get(clave)

    async def get_stale(self, clave: str) -> Any | None:
        if self._redis_disponible:
            try:
                raw = await self._r.get(f"{clave}:stale")
                if raw is not None:
                    return json.loads(raw)
            except RedisError:
                self._registrar_fallo()

        return await self._memory.get_stale(clave)

    async def set(
        self, clave: str, valor: Any, ttl: int | None = None
    ) -> None:
        if ttl is None:
            ttl = get_settings().cache_ttl_seconds

        # Conservamos una copia local para contingencias.
        await self._memory.set(clave, valor, ttl)

        if self._redis_disponible:
            try:
                raw = json.dumps(valor, default=str)

                await self._r.set(clave, raw, ex=ttl)
                await self._r.set(f"{clave}:stale", raw)

            except RedisError:
                self._registrar_fallo()


_cache = None


def get_cache():
    """Selecciona Redis o memoria según la configuración."""
    global _cache

    if _cache is None:
        url = get_settings().redis_url

        if url:
            try:
                _cache = RedisCache(url)
            except Exception:
                log.exception(
                    "No se pudo inicializar Redis; "
                    "usando memoria"
                )
                _cache = MemoryCache()
        else:
            _cache = MemoryCache()

    return _cache

