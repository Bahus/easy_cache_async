from .base import BaseCacheBackend
from ..core import DEFAULT_TIMEOUT, NOT_FOUND


class DummyCacheInstance(BaseCacheBackend):
    """Dummy cache instance"""

    async def delete(self, key):
        pass

    async def set(self, key, value, timeout=DEFAULT_TIMEOUT):
        pass

    async def get(self, key, default=NOT_FOUND):
        return default

    async def set_many(self, data_dict, timeout=DEFAULT_TIMEOUT):
        pass

    async def get_many(self, keys):
        return {}
