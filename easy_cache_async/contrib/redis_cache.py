from .base import BaseCacheInstance, SerializerMixin
from easy_cache_async.core import DEFAULT_TIMEOUT, NOT_FOUND


class RedisCacheInstance(SerializerMixin, BaseCacheInstance):
    """Redis cache instance compatible with easy_cache.

    Instance of aioredis.Redis instance must be passed to init.
    See: https://pypi.python.org/pypi/aioredis
    """
    def __init__(self, client, **options):
        """
        :type client: aioredis.Redis
        """
        self.client = client
        super().__init__(**options)

    async def get_many(self, keys) -> dict:
        return dict(
            zip(
                keys,
                map(self.load_value, await self.client.mget(self.make_keys(keys)))
            )
        )

    async def set(self, key, value, timeout=DEFAULT_TIMEOUT):
        """
            :param timeout: must be in seconds
        """
        if timeout is DEFAULT_TIMEOUT:
            timeout = None

        return await self.client.set(
            self.make_key(key),
            self.dump_value(value),
            expire=timeout
        )

    async def set_many(self, data_dict: dict, timeout=DEFAULT_TIMEOUT):
        """
            :param timeout: must be in seconds
        """
        if timeout is DEFAULT_TIMEOUT:
            timeout = None

        pipe = self.client.pipeline()
        pipe.mset(
            {self.make_key(key): self.dump_value(value)
             for key, value in data_dict.items()}
        )

        if timeout:
            for key in data_dict:
                pipe.expire(self.make_key(key), timeout)

        return await pipe.execute()

    async def delete(self, key):
        return await self.client.delete(self.make_key(key))

    async def get(self, key, default=NOT_FOUND):
        result = await self.client.get(self.make_key(key))
        return default if result is None else self.load_value(result)
