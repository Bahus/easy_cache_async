import inspect
import random
from functools import partial
from unittest.mock import Mock

import pytest
from cachetools import Cache

from easy_cache_async import ecached, ecached_property, meta_accepted, set_global_cache_instance
from easy_cache_async.compat import force_text
from easy_cache_async.contrib.locmem_cache import LocMemCacheInstance
from easy_cache_async.core import DEFAULT_TIMEOUT, MetaCallable, create_cache_key, \
    create_tag_cache_key, invalidate_cache_key, invalidate_cache_tags


@pytest.fixture()
def local_cache():
    return CacheInstanceProxy(
        cache_instance=LocMemCacheInstance(Cache(100))
    )


@pytest.fixture()
def user():
    return User(random.randint(1, 100))


cache_mock = Mock()


def custom_cache_key(*args, **kwargs):
    return create_cache_key('my_prefix', args[0].id, *args[1:])


def get_test_result(*args, **kwargs):
    result = process_args(*args, **kwargs)
    cache_mock(result)
    return result


def choose_timeout(self, a, b, c):
    if not isinstance(a, int):
        return DEFAULT_TIMEOUT
    return a * 100


@ecached(timeout=100)
async def computation(a, b, c):
    return get_test_result(a, b, c)


class User:
    name = 'user_name'
    prefixed_ecached = partial(ecached, prefix='USER:{self.id}', timeout=3600)

    def __init__(self, uid):
        self.id = uid

    @ecached('dyn_timeout:{a}', timeout=choose_timeout)
    def instance_dynamic_timeout(self, a, b, c):
        return get_test_result(a, b, c)

    @ecached()
    def instance_default_cache_key(self, a, b, c=8):
        return get_test_result(a, b, c)

    @ecached()
    @classmethod
    def class_method_default_cache_key(cls, a, b, c=9, d='Иван'):
        return get_test_result(a, b, c)

    @ecached_property()
    def test_property(self):
        return get_test_result('property')

    @ecached('{self.id}:{a}:{b}:{c}')
    def instance_method_string(self, a, b, c=10):
        return get_test_result(a, b, c)

    @ecached(['self.id', 'a', 'b'])
    def instance_method_list(self, a, b, c=11):
        return get_test_result(a, b, c)

    @ecached(custom_cache_key)
    def instance_method_callable(self, a, b, c=12):
        return get_test_result(a, b, c)

    @ecached('{self.id}:{a}:{b}', 400)
    def instance_method_timeout(self, a, b, c=13):
        return get_test_result(a, b, c)

    @ecached('{self.id}:{a}:{b}', 500, ('tag1', 'tag2'))
    def instance_method_tags(self, a, b, c=14):
        return get_test_result(a, b, c)

    @staticmethod
    def generate_custom_tags(meta):
        """ :type meta: MetaCallable """
        if meta.has_returned_value:
            cache_mock.assert_called_with(meta.returned_value)

        self = meta.args[0]
        a = meta.args[1]
        return [create_cache_key(self.name, self.id, a), 'simple_tag']

    @meta_accepted
    @staticmethod
    def generate_key_based_on_meta(m, a=1):
        assert isinstance(m, MetaCallable)
        assert m.function is getattr(m['self'], 'instance_method_meta_test').function
        assert m.scope is m['self']
        assert a == 1

        return create_cache_key(m['a'], m['b'], m['c'])

    @ecached(generate_key_based_on_meta)
    def instance_method_meta_test(self, a, b, c=666):
        return get_test_result(a, b, c)

    @ecached('{a}:{b}', tags=generate_custom_tags)
    def instance_method_custom_tags(self, a, b, c=14):
        return get_test_result(a, b, c)

    @prefixed_ecached('p1:{a}:{b}:{c}', tags=['{self.id}:tag1'])
    def instance_method_prefixed(self, a, b, c=15):
        return get_test_result(a, b, c)

    @ecached_property('{self.id}:friends_count', timeout=100, prefix='USER_PROPERTY')
    def friends_count(self):
        cache_mock()
        return 15

    @ecached_property('static_key')
    def property_no_tags(self):
        cache_mock()
        return '42'

    @ecached(cache_key='{cls.name}:{c}')
    @classmethod
    def class_method_cache_key_string(cls, a, b, c=17):
        return get_test_result(a, b, c)

    @ecached(('cls.name', 'a'), 500, ['tag4', 'tag5:{cls.name}'],
             prefix=lambda cls, *args, **kwargs: create_cache_key('USER', args[0], args[1]))
    @classmethod
    def class_method_full_spec(cls, a, b, c=18):
        return get_test_result(a, b, c)

    @ecached('{hg}:{hg}:{test}', prefix=u'пользователь')
    @staticmethod
    def static_method(hg, test='abc', n=1.1):
        return get_test_result(hg, test, n)

    @ecached(tags=['ttt:{c}'], prefix='ppp:{b}')
    @staticmethod
    def static_method_default_key(a, b, c=11):
        return get_test_result(a, b, c)


@pytest.mark.usefixtures('setup')
@pytest.mark.asyncio
class TestClassCachedDecorator:

    @staticmethod
    def get_user():
        return User(random.randint(1, 1000))

    # noinspection PyAttributeOutsideInit
    @pytest.fixture()
    def setup(self, local_cache, event_loop):
        self.cache_mock = cache_mock
        self.cache_mock.reset_mock()

        self.local_cache = local_cache
        set_global_cache_instance(self.local_cache.cache_instance)
        self.user = self.get_user()
        self.user_class = self.user.__class__
        self.user_class_name = self.user_class.__name__
        self.event_loop = event_loop

        yield
        self.cache_mock.reset_mock()
        event_loop.run_until_complete(self.local_cache.clear())

        del self.cache_mock
        del self.local_cache
        del self.user
        del self.user_class
        del self.user_class_name
        del self.event_loop

    @staticmethod
    async def _get_property_value(value):
        if inspect.iscoroutine(value):
            return await value
        return value

    async def _check_base(self, _callable, param_to_change=None):
        self.cache_mock.reset_mock()

        items = ['юла', 'str', 100, 1.45]
        random.shuffle(items)

        a, b, c = items[:3]

        result = process_args(a, b, c)

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

        result = process_args(a, b, c)

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

    # Tests
    async def test_default_cache_key(self):
        cache_callable = self.user.instance_default_cache_key
        cache_key = create_cache_key(
            __name__ + '.{}.instance_default_cache_key'.format(self.user_class_name), 1, 2, 8
        )
        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, 1, 2)
        await self._check_timeout(cache_key, DEFAULT_TIMEOUT)

        cache_callable = self.user_class.class_method_default_cache_key
        cache_key = create_cache_key(
            __name__ + '.{}.class_method_default_cache_key'.format(self.user_class_name),
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
            assert await self._get_property_value(self.user.test_property) == 'property'

        await check_property()
        cache_callable = lambda: getattr(self.user, 'test_property')
        cache_callable.property = True

        cache_key = create_cache_key(__name__ + '.{}.test_property'.format(self.user_class_name))

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
        result = process_args(a, b, c)
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
        cache_tags = self.user.generate_custom_tags(MetaCallable(args=(self.user, 10)))

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
        assert await self._get_property_value(self.user.friends_count) == 15

        cache_callable = lambda: getattr(self.user, 'friends_count')
        cache_callable.property = True
        cache_callable.invalidate_cache_by_prefix = self.user_class.friends_count.invalidate_cache_by_prefix

        cache_prefix = 'USER_PROPERTY'
        cache_key = create_cache_key(cache_prefix, self.user.id, 'friends_count')

        await self._check_cache_key(cache_callable, cache_key)
        await self._check_timeout(cache_key, 100)
        await self._check_cache_prefix(cache_callable, cache_prefix)

    async def test_property_no_tags(self):
        assert await self._get_property_value(self.user.property_no_tags) == '42'

        cache_callable = lambda: getattr(self.user, 'property_no_tags')
        cache_callable.property = True
        cache_key = create_cache_key('static_key')

        await self._check_cache_key(cache_callable, cache_key)

    async def test_class_method_key_string(self):
        cache_callable = self.user_class.class_method_cache_key_string
        cache_key = create_cache_key(User.name, 17)

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
        cache_key = create_cache_key(cache_prefix, User.name, a)

        await self._check_base(cache_callable)
        await self._check_cache_key(cache_callable, cache_key, a, b, c)
        await self._check_timeout(cache_key, 500)
        await self._check_tags(
            cache_callable,
            ['tag4', create_cache_key('tag5', User.name)],
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
            cache_prefix, __name__ + '.{}.static_method_default_key'.format(self.user_class_name),
            1, 2, 11
        )

        await self._check_base(cache_callable, param_to_change='b')
        await self._check_cache_key(cache_callable, cache_key, a=1, b=2)

        # check partial invalidation
        self.cache_mock.reset_mock()
        self.cache_mock.assert_not_called()

        await cache_callable(1, 2, 3)
        self.cache_mock.assert_called_once_with(process_args(1, 2, 3))
        self.cache_mock.reset_mock()

        await cache_callable(1, 2, 3)
        self.cache_mock.assert_not_called()
        self.cache_mock.reset_mock()

        await cache_callable.invalidate_cache_by_tags(c=3)
        await cache_callable(1, 2, 3)
        self.cache_mock.assert_called_once_with(process_args(1, 2, 3))
        self.cache_mock.reset_mock()

        await cache_callable.invalidate_cache_by_prefix(b=2)
        await cache_callable(1, 2, 3)
        self.cache_mock.assert_called_once_with(process_args(1, 2, 3))
        self.cache_mock.reset_mock()

        await cache_callable.invalidate_cache_by_key(1, b=2, c=3)
        await cache_callable(1, 2, 3)
        self.cache_mock.assert_called_once_with(process_args(1, 2, 3))

    #
    # async def test_instance_method_and_meta_accepted_decorator(self):
    #     cache_callable = self.user.instance_method_meta_test
    #
    #     cache_key = create_cache_key(1, 2, 5)
    #
    #     await self._check_base(cache_callable)
    #     await self._check_cache_key(cache_callable, cache_key, 1, 2, c=5)
    #     await self._check_timeout(cache_key, DEFAULT_TIMEOUT)
    #     self.assertEqual(len(self.local_cache), 1)
    #
    # async def test_instance_method_dynamic_timeout(self):
    #     cache_callable = self.user.instance_dynamic_timeout
    #
    #     await self._check_base(cache_callable)
    #
    #     cache_key = create_cache_key('dyn_timeout', 2)
    #     await self._check_cache_key(cache_callable, cache_key, 2, 3, 4)
    #     await self._check_timeout(cache_key, 2 * 100)
    #
    #     self.cache_mock.reset_mock()
    #
    #     cache_key = create_cache_key('dyn_timeout', 4)
    #     await self._check_cache_key(cache_callable, cache_key, 4, 5, 6)
    #     await self._check_timeout(cache_key, 4 * 100)
    #

