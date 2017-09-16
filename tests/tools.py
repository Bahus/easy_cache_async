import inspect
import random
from abc import ABC, abstractmethod
from unittest.mock import Mock

import pytest
import typing

from easy_cache_async import create_tag_cache_key, invalidate_cache_key, invalidate_cache_tags, set_global_cache_instance

from easy_cache_async.contrib.base import BaseCacheInstance
from easy_cache_async.contrib.redis_cache import RedisCacheInstance
from easy_cache_async.core import DEFAULT_TIMEOUT
from easy_cache_async.utils import force_text


CacheType = typing.Union[BaseCacheInstance, RedisCacheInstance]


class AbstractCacheInstanceProxy(ABC):

    def __init__(self, cache_instance: CacheType):
        self.cache_instance = cache_instance

    def __getattr__(self, item):
        return getattr(self.cache_instance, item)

    @abstractmethod
    async def get_timeout(self, key):
        """Get timeout for provided key"""

    @abstractmethod
    async def clear(self):
        """Clear cache and all related data"""

    @abstractmethod
    async def get_all_keys(self) -> typing.Sequence:
        """List all keys in a cache instance"""

    @abstractmethod
    async def contains(self, key) -> bool:
        """If cache contains provided key"""

    @classmethod
    @abstractmethod
    def create(cls, **kwargs):
        """Create specific proxy instance"""
        pass

    async def get_len(self):
        return len(await self.get_all_keys())

    def with_key_prefix(self, value=''):
        return value

    async def search_prefix(self, prefix) -> bool:
        keys_list = await self.get_all_keys()
        actual_prefix = self.with_key_prefix(prefix)

        for key in keys_list:
            # force all keys to be unicode, since not all cache backends support it
            key = force_text(key)
            if key.startswith(actual_prefix):
                return True

        return False


class CacheMock(Mock):

    @staticmethod
    def create_args(*args, **kwargs):
        final = list(args)
        for k, v in sorted(kwargs.items()):
            final.append(k)
            final.append(v)

        return ':'.join(force_text(i) for i in final)

    def trigger_result(self, *args, **kwargs):
        result = self.create_args(*args, **kwargs)
        self(result)
        return result


class BaseTest(ABC):

    @staticmethod
    @abstractmethod
    def get_cache_mock() -> CacheMock:
        pass

    def setup_test(self):
        pass

    def teardown_test(self):
        pass

    # noinspection PyAttributeOutsideInit
    @pytest.fixture()
    def setup(self, event_loop, cache_proxy):
        self.event_loop = event_loop
        self.cache_mock = self.get_cache_mock()
        self.local_cache = cache_proxy
        set_global_cache_instance(self.local_cache.cache_instance)
        self.setup_test()

        yield

        self.cache_mock.reset_mock()
        self.teardown_test()

        del self.event_loop
        del self.cache_mock
        del self.local_cache

    @staticmethod
    async def _get_awaitable_value(value):
        if inspect.iscoroutine(value):
            return await value
        return value

    async def _check_base(self, _callable, param_to_change=None):
        self.cache_mock.reset_mock()

        items = ['юла', 'str', 100, 1.45]
        random.shuffle(items)

        a, b, c = items[:3]

        result = self.cache_mock.create_args(a, b, c)

        assert await _callable(a, b, c) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        # cached version (force convert to unicode)
        assert force_text(await _callable(a, b, c)) == force_text(result)
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

        if param_to_change == 'c':
            c = items[3]
        elif param_to_change == 'b':
            b = items[3]
        else:
            a = items[3]

        result = self.cache_mock.create_args(a, b, c)

        # different params, no cache
        assert await _callable(a, b, c) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

    async def _check_cache_key(self, _callable, cache_key, *args, **kwargs):
        await self.local_cache.clear()

        assert not await self.local_cache.contains(cache_key)

        await _callable(*args, **kwargs)

        assert await self.local_cache.contains(cache_key)

        as_property = getattr(_callable, 'property', False)
        if as_property:
            await invalidate_cache_key(cache_key)
        else:
            await _callable.invalidate_cache_by_key(*args, **kwargs)

        assert not await self.local_cache.contains(cache_key)
        # perform actual call
        await _callable(*args, **kwargs)

    async def _check_cache_prefix(self, _callable, prefix, *args, **kwargs):
        await self.local_cache.clear()
        self.cache_mock.reset_mock()

        tag_prefix = create_tag_cache_key(prefix)
        assert not await self.local_cache.contains(tag_prefix)

        result = await _callable(*args, **kwargs)
        assert await self.local_cache.contains(tag_prefix)
        assert await self.local_cache.search_prefix(prefix)

        as_property = getattr(_callable, 'property', False)
        if as_property:
            self.cache_mock.assert_called_once_with()
        else:
            self.cache_mock.assert_called_once_with(result)

        self.cache_mock.reset_mock()

        await _callable(*args, **kwargs)

        self.cache_mock.assert_not_called()

        await _callable.invalidate_cache_by_prefix(*args, **kwargs)
        result = await _callable(*args, **kwargs)

        if as_property:
            self.cache_mock.assert_called_once_with()
        else:
            self.cache_mock.assert_called_once_with(result)

        self.cache_mock.reset_mock()

    async def _check_timeout(self, cache_key, timeout):
        if timeout is DEFAULT_TIMEOUT:
            timeout = None

        cache_key_exists = await self.local_cache.contains(cache_key)
        assert cache_key_exists, '_check_cache_key required to use this method'
        assert await self.local_cache.get_timeout(cache_key) == timeout

    async def _check_tags(self, _callable, tags, *args, **kwargs):
        await self.local_cache.clear()
        self.cache_mock.reset_mock()

        for tag in tags:
            assert not await self.local_cache.contains(create_tag_cache_key(tag))

        result = await _callable(*args, **kwargs)

        for tag in tags:
            assert await self.local_cache.contains(create_tag_cache_key(tag))

        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        # invalidate by tag
        for tag in tags:
            await invalidate_cache_tags(tag)
            result = await _callable(*args, **kwargs)
            self.cache_mock.assert_called_once_with(result)
            self.cache_mock.reset_mock()

            await _callable(*args, **kwargs)
            assert not self.cache_mock.called

            await _callable.invalidate_cache_by_tags(tag, *args, **kwargs)
            result = await _callable(*args, **kwargs)
            self.cache_mock.assert_called_once_with(result)
            self.cache_mock.reset_mock()


class AsyncMock(Mock):

    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)
