import typing

from cachetools import Cache
import aioredis

from easy_cache_async.contrib.locmem_cache import CachedValue, LocMemCacheInstance
from easy_cache_async.contrib.redis_cache import RedisCacheInstance
from easy_cache_async.core import NOT_FOUND
from .tools import AbstractCacheInstanceProxy


class LocMemCacheProxy(AbstractCacheInstanceProxy):

    async def get_timeout(self, key):
        value = self.client.get(self.make_key(key), NOT_FOUND)  # type: CachedValue
        assert value is not NOT_FOUND
        assert isinstance(value, CachedValue)

        return value.timeout

    async def clear(self):
        self.cache_instance.client.clear()

    async def contains(self, key) -> bool:
        return key in self.cache_instance.client

    async def get_all_keys(self) -> typing.Sequence:
        return list(self.cache_instance.client.keys())

    @classmethod
    def create(cls, cache_class=Cache, **kwargs):
        return cls(LocMemCacheInstance(cache_class(**kwargs)))


class RedisCacheProxy(AbstractCacheInstanceProxy):

    async def get_all_keys(self) -> typing.Sequence:
        return await self.cache_instance.client.keys('*')

    async def clear(self):
        return await self.cache_instance.client.flushall()

    async def contains(self, key) -> bool:
        return await self.cache_instance.client.exists(key)

    async def get_timeout(self, key):
        result = await self.cache_instance.client.ttl(key)
        if result == -1:
            return None
        return result

    @classmethod
    async def create(cls, **kwargs):
        from .conftest import REDIS_CONNECTION
        redis = await aioredis.create_redis(REDIS_CONNECTION)
        return cls(cache_instance=RedisCacheInstance(redis, **kwargs))
