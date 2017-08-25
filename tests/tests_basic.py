import pytest

from easy_cache_async import ecached, invalidate_cache_key, invalidate_cache_prefix
from easy_cache_async.core import create_cache_key
from .tools import CacheMock, BaseTest
from .proxies import LocMemCacheProxy


cache_mock = CacheMock()


@ecached(('kwargs[a]', 'kwargs[b]'), prefix='пользователь')
async def ordinal_func(*args, **kwargs):
    return cache_mock.trigger_result(*args, **kwargs)


@ecached('second:{c}', timeout=450, tags=['{a}'])
async def second_func(a, b, c=100):
    return cache_mock.trigger_result(a, b, c)


@pytest.mark.usefixtures('setup')
@pytest.mark.asyncio
class TestBasicLocMemCache(BaseTest):

    @staticmethod
    def get_local_cache():
        return LocMemCacheProxy.create(maxsize=100)

    @staticmethod
    def get_cache_mock() -> CacheMock:
        return cache_mock

    async def test_ordinal_func(self):
        cache_callable = ordinal_func
        cache_prefix = ordinal_func.prefix
        cache_key = create_cache_key(cache_prefix, 10, 20)

        result = self.cache_mock.create_args(a=10, b=10)

        assert await cache_callable(a=10, b=10) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        # cached version
        assert await cache_callable(a=10, b=10) == result
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

        result = self.cache_mock.create_args(a=10, b=22)

        # different params, no cache
        assert await cache_callable(a=10, b=22) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        await self._check_cache_key(cache_callable, cache_key, a=10, b=20)
        await self._check_cache_prefix(cache_callable, cache_prefix, a=10, b=20)

    async def test_second_func(self):
        cache_callable = second_func
        cache_key = create_cache_key('second', 100)

        await self._check_base(cache_callable, param_to_change='c')
        await self._check_cache_key(cache_callable, cache_key, 1, 2, c=100)
        await self._check_timeout(cache_key, 450)
        await self._check_tags(cache_callable, ['yyy'], 'yyy', 111)

    async def test_invalidators(self):
        a, b = 'a', 'b'
        cache_callable = ordinal_func
        cache_prefix = ordinal_func.prefix
        cache_key = create_cache_key(cache_prefix, a, b)

        result = self.cache_mock.create_args(a=a, b=b)

        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        # cached version
        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

        # invalidate cache via cache key
        await invalidate_cache_key(cache_key)

        # second invalidation should fail silently
        await invalidate_cache_key(cache_key)

        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        # cached version
        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

        # invalidate cache via prefix
        await invalidate_cache_prefix(cache_prefix)
        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        # cached version
        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

        # invalidate cache via attached invalidator
        await cache_callable.invalidate_cache_by_key(a=a, b=b)
        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

    async def test_refresh_cache(self):
        a, b = 'я', 'b'
        cache_callable = ordinal_func

        self.cache_mock.reset_mock()

        result = self.cache_mock.create_args(a=a, b=b)

        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        # cached version
        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

        # refresh cache via cache key
        await cache_callable.refresh_cache(a=a, b=b)
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        assert await cache_callable(a=a, b=b) == result
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()
