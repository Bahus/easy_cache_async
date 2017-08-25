from .base import BaseCacheInstance

from collections import namedtuple
from asyncio import Lock
from easy_cache_async.core import DEFAULT_TIMEOUT, NOT_FOUND, get_timestamp


class CachedValue(namedtuple('CachedValue', ['value', 'timeout', 'timestamp'])):

    @property
    def is_valid(self):
        if self.timeout is DEFAULT_TIMEOUT:
            return True

        return (self.timeout * 1000000 + self.timestamp) >= get_timestamp()


class LocMemCacheInstance(BaseCacheInstance):
    """Memory cache instance compatible with easy_cache_async

    Instance of cachetools.Cache (and derivatives) must be passed to init.
    See: https://pypi.python.org/pypi/cachetools
    """

    def __init__(self, client, **options):
        """
        :type client: cachetools.Cache
        """
        self.client = client
        self.lock = Lock()
        super().__init__(**options)

    async def get(self, key, default=NOT_FOUND):
        return self.sget(key, default)

    def sget(self, key, default=NOT_FOUND):
        value = self.client.get(self.make_key(key), NOT_FOUND)  # type: CachedValue

        if value is NOT_FOUND:
            return default

        return value.value if value.is_valid else default

    async def set(self, key, value, timeout=DEFAULT_TIMEOUT):
        # TODO: this is not thread safe lock
        async with self.lock:
            self.client[self.make_key(key)] = CachedValue(value, timeout, get_timestamp())

    async def delete(self, key):
        try:
            del self.client[self.make_key(key)]
            return True
        except KeyError:
            # fail silently
            return False

    async def get_many(self, keys):
        return {key: self.sget(key, default=None) for key in keys}

    async def set_many(self, data_dict: dict, timeout=DEFAULT_TIMEOUT):
        timestamp = get_timestamp()

        # TODO: this is not thread safe lock
        async with self.lock:
            self.client.update({
                self.make_key(key): CachedValue(value, timeout, timestamp)
                for key, value in data_dict.items()
            })
