
import pytest

from jeils.cache import MemoryCache


@pytest.mark.asyncio
async def test_guardar_y_recuperar_cache():
    cache = MemoryCache()

    await cache.set("prueba", {"dato": "JEILS"}, ttl=60)

    resultado = await cache.get("prueba")

    assert resultado == {"dato": "JEILS"}


@pytest.mark.asyncio
async def test_cache_vencida():
    cache = MemoryCache()

    await cache.set("prueba", {"dato": "antiguo"}, ttl=0)

    resultado = await cache.get("prueba")

    assert resultado is None


@pytest.mark.asyncio
async def test_recuperar_cache_stale():
    cache = MemoryCache()

    await cache.set("prueba", {"dato": "respaldo"}, ttl=0)

    resultado = await cache.get_stale("prueba")

    assert resultado == {"dato": "respaldo"}



@pytest.mark.asyncio
async def test_respaldo_cuando_redis_falla(monkeypatch):
    from redis.exceptions import ConnectionError

    from jeils.cache import RedisCache

    class RedisSimulado:
        async def set(self, *args, **kwargs):
            raise ConnectionError("Redis no disponible")

        async def get(self, *args, **kwargs):
            raise ConnectionError("Redis no disponible")

    cache = RedisCache("redis://localhost:6379")

    # Simulamos que Redis deja de funcionar.
    monkeypatch.setattr(cache, "_r", RedisSimulado())

    # El sistema debe guardar el dato en memoria.
    await cache.set(
        "senamhi:prueba",
        {"temperatura": 25},
        ttl=60,
    )

    resultado = await cache.get("senamhi:prueba")

    assert resultado == {"temperatura": 25}
    assert cache._redis_disponible is False
