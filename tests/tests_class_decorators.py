import random

import pytest

from easy_cache_async import ecached
from easy_cache_async.core import DEFAULT_TIMEOUT, MetaCallable, create_cache_key

from .fixtures import (
    AsyncUser,
    User,
    __name__ as __test_name__,
    custom_cache_key,
)
from .tools import BaseTest, CacheMock


cache_mock = CacheMock()


@ecached(timeout=100)
async def computation(a, b, c):
    return cache_mock.trigger_result(a, b, c)


@pytest.mark.usefixtures('setup')
@pytest.mark.asyncio
class TestClassCachedDecorator(BaseTest):

    @staticmethod
    def get_cache_mock() -> CacheMock:
        return cache_mock

    @staticmethod
    def get_user():
        return User(random.randint(1, 1000), cache_mock)

    # noinspection PyAttributeOutsideInit
    def setup_test(self):
        self.user = self.get_user()
        self.user_class = self.user.__class__
        self.user_class_name = self.user_class.__name__

    def teardown_test(self):
        del self.user
        del self.user_class
        del self.user_class_name

    async def test_default_cache_key(self):
        cache_callable = self.user.instance_default_cache_key
        cache_key = create_cache_key(
            __test_name__ + '.{}.instance_default_cache_key'.format(self.user_class_name), 1, 2, 8
        )
        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 1, 2)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)

        cache_callable = self.user_class.class_method_default_cache_key
        cache_key = create_cache_key(
            __test_name__ + '.{}.class_method_default_cache_key'.format(self.user_class_name),
            2, 3, 9, 'Иван'
        )

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 2, 3)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)

        cache_callable = computation
        cache_key = create_cache_key(
            __name__ + '.computation', 'a', 'b', 'c'
        )

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 'a', 'b', 'c')
        await self._check_timeout(cache_key, 100)

    async def test_default_cache_key_for_property(self):
        async def check_property():
            assert await self._get_awaitable_value(self.user.test_property) == 'property'

        await check_property()
        cache_callable = lambda: getattr(self.user, 'test_property')
        cache_callable.property = True

        cache_key = create_cache_key(__test_name__ + '.{}.test_property'.format(self.user_class_name))

        await self._check_cache_key(cache_callable, cache_key)

        await self.local_cache.clear()
        self.cache_mock.reset_mock()

        await check_property()
        self.cache_mock.assert_called_once_with('property')
        self.cache_mock.reset_mock()

        await check_property()
        self.cache_mock.assert_not_called()

        # invalidate cache
        await self.user_class.test_property.invalidate_cache_by_key()
        await check_property()
        self.cache_mock.assert_called_once_with('property')

    async def test_issue_8_cache_key_for_property(self):
        async def check_property():
            assert await self._get_awaitable_value(self.user.issue_8_test_property) == 'issue_8_property'

        await check_property()
        cache_callable = lambda: getattr(self.user, 'issue_8_test_property')
        cache_callable.property = True

        cache_key = create_cache_key('manufacturer:{}'.format(self.user.id))

        await self._check_cache_key(cache_callable, cache_key)

        await self.local_cache.clear()
        self.cache_mock.reset_mock()

        await check_property()
        self.cache_mock.assert_called_once_with('issue_8_property')
        self.cache_mock.reset_mock()

        await check_property()
        self.cache_mock.assert_not_called()

        # invalidate cache
        await self.user_class.issue_8_test_property.invalidate_cache_by_key(self.user)
        await check_property()
        self.cache_mock.assert_called_once_with('issue_8_property')


    async def test_cache_key_as_string(self):
        cache_callable = self.user.instance_method_string
        cache_key = create_cache_key(self.user.id, 1, 2, 3)

        await self._check_base(self.user.instance_method_string)
        await self._check_cache_key(cache_callable, cache_key, 1, 2, c=3)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)
        assert await self.local_cache.get_len() == 1

    async def test_cache_key_as_list(self):
        cache_callable = self.user.instance_method_list
        cache_key = create_cache_key(self.user.id, 2, 3)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 2, 3)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)

    async def test_cache_key_as_list_unrelated_param_changed(self):
        # if we change only "c" parameter - data will be received from cache
        a = b = c = 10
        result = self.cache_mock.create_args(a, b, c)
        assert await self.user.instance_method_list(a, b, c) == result
        self.cache_mock.assert_called_once_with(result)
        self.cache_mock.reset_mock()

        # still cached version
        assert await self.user.instance_method_list(a, b, c + 10) == result
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

    async def test_cache_key_as_callable(self):
        cache_callable = self.user.instance_method_callable
        cache_key = custom_cache_key(self.user, 5, 5)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 5, 5)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)

    async def test_not_default_timeout(self):
        cache_callable = self.user.instance_method_timeout
        cache_key = create_cache_key(self.user.id, 5, 5)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 5, 5)
        await self._check_timeout(cache_key, 400)

    async def test_cache_tags(self):
        cache_callable = self.user.instance_method_tags
        cache_key = create_cache_key(self.user.id, 5, 5)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 5, 5)
        await self._check_timeout(cache_key, 500)
        await self._check_tags(cache_callable, ['tag1', 'tag2'], 6, 7)

    async def test_cache_custom_tags(self):
        cache_callable = self.user.instance_method_custom_tags
        cache_key = create_cache_key(10, 11)
        cache_tags = await self._get_awaitable_value(
            self.user.generate_custom_tags(MetaCallable(args=(self.user, 10)))
        )

        await self._check_cache_key(cache_callable, cache_key, 10, 11)
        await self._check_tags(cache_callable, cache_tags, 10, 11)

    async def test_method_prefixed(self):
        cache_callable = self.user.instance_method_prefixed
        cache_prefix = create_cache_key('USER', self.user.id)

        # prefix should ba attached
        cache_key = create_cache_key(cache_prefix, 'p1', 1, 2, 3)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 1, 2, 3)
        await self._check_timeout(cache_key, 3600)

        # prefix is a tag actually
        await self._check_cache_prefix(cache_callable, cache_prefix, 1, 2, 3)
        await self._check_tags(cache_callable, [create_cache_key(self.user.id, 'tag1')], 1, 2, 3)

    async def test_property_friends_count(self):
        assert await self._get_awaitable_value(self.user.friends_count) == 15

        cache_callable = lambda: getattr(self.user, 'friends_count')
        cache_callable.property = True
        cache_callable.invalidate_cache_by_prefix = (
            self.user_class.friends_count.invalidate_cache_by_prefix
        )

        cache_prefix = 'USER_PROPERTY'
        cache_key = create_cache_key(cache_prefix, self.user.id, 'friends_count')

        await self._check_cache_key(cache_callable, cache_key)
        await self._check_timeout(cache_key, 100)
        await self._check_cache_prefix(cache_callable, cache_prefix)

    async def test_property_no_tags(self):
        assert await self._get_awaitable_value(self.user.property_no_tags) == '42'

        cache_callable = lambda: getattr(self.user, 'property_no_tags')
        cache_callable.property = True
        cache_key = create_cache_key('static_key')

        await self._check_cache_key(cache_callable, cache_key)

    async def test_class_method_key_string(self):
        cache_callable = self.user_class.class_method_cache_key_string
        cache_key = create_cache_key(self.user_class.name, 17)

        await self._check_base(cache_callable, param_to_change='c')
        await self._check_cache_key(cache_callable, cache_key, 1, 2)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)

        cache_callable = self.user.class_method_cache_key_string
        await self._check_base(cache_callable, param_to_change='c')
        await self._check_cache_key(cache_callable, cache_key, 4, 5)

    async def test_class_method_full_spec(self):
        cache_callable = self.user_class.class_method_full_spec
        a = 'ф'
        b = 'ю'
        c = 10

        cache_prefix = create_cache_key('USER', a, b)
        cache_key = create_cache_key(cache_prefix, self.user_class.name, a)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, a, b, c)
        await self._check_timeout(cache_key, 500)
        await self._check_tags(
            cache_callable,
            ['tag4', create_cache_key('tag5', self.user_class.name)],
            a, b, c
        )
        await self._check_cache_prefix(cache_callable, cache_prefix, a, b, c)

    async def test_static_method(self):
        cache_callable = self.user_class.static_method
        hg = 123
        test = 'ЫЮЯ'

        cache_prefix = cache_callable.prefix
        cache_key = create_cache_key(cache_prefix, hg, hg, test)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, hg, test)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)
        await self._check_cache_prefix(cache_callable, cache_prefix, hg, test)

    async def test_static_method_default_key(self):
        cache_callable = self.user_class.static_method_default_key
        cache_prefix = create_cache_key('ppp', 2)
        cache_key = create_cache_key(
            cache_prefix, __test_name__ + '.{}.static_method_default_key'.format(self.user_class_name),
            1, 2, 11
        )

        await self._check_base(cache_callable, param_to_change='b')
        await self._check_cache_key(cache_callable, cache_key, a=1, b=2)

        # check partial invalidation
        self.cache_mock.reset_mock()
        self.cache_mock.assert_not_called()

        await cache_callable(1, 2, 3)
        self.cache_mock.assert_called_once_with(self.cache_mock.create_args(1, 2, 3))
        self.cache_mock.reset_mock()

        await cache_callable(1, 2, 3)
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

        await cache_callable.invalidate_cache_by_tags(c=3)
        await cache_callable(1, 2, 3)
        self.cache_mock.assert_called_once_with(self.cache_mock.create_args(1, 2, 3))
        self.cache_mock.reset_mock()

        await cache_callable.invalidate_cache_by_prefix(b=2)
        await cache_callable(1, 2, 3)
        self.cache_mock.assert_called_once_with(self.cache_mock.create_args(1, 2, 3))
        self.cache_mock.reset_mock()

        await cache_callable.invalidate_cache_by_key(1, b=2, c=3)
        await cache_callable(1, 2, 3)
        self.cache_mock.assert_called_once_with(self.cache_mock.create_args(1, 2, 3))

    async def test_instance_method_and_meta_accepted_decorator(self):
        cache_callable = self.user.instance_method_meta_test

        cache_key = create_cache_key(1, 2, 5)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 1, 2, c=5)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)
        assert await self.local_cache.get_len() == 1

    async def test_instance_method_dynamic_timeout(self):
        cache_callable = self.user.instance_dynamic_timeout

        await self._check_base(cache_callable)

        cache_key = create_cache_key('dyn_timeout', 2)
        await self._check_cache_key(cache_callable, cache_key, 2, 3, 4)
        await self._check_timeout(cache_key, 2 * 100)

        self.cache_mock.reset_mock()

        cache_key = create_cache_key('dyn_timeout', 4)
        await self._check_cache_key(cache_callable, cache_key, 4, 5, 6)
        await self._check_timeout(cache_key, 4 * 100)


class TestClassCachedDecoratorAsync(TestClassCachedDecorator):

    @staticmethod
    def get_user():
        return AsyncUser(random.randint(1, 1000), cache_mock)
