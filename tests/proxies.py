import typing
from cachetools import Cache

from easy_cache_async.contrib.locmem_cache import CachedValue, LocMemCacheInstance
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
    def create(cls, **kwargs):
        return cls(LocMemCacheInstance(Cache(**kwargs)))
