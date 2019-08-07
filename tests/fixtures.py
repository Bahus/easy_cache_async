from functools import partial

from easy_cache_async import (
    MetaCallable,
    create_cache_key,
    ecached,
    ecached_property,
    meta_accepted,
)
from easy_cache_async.core import DEFAULT_TIMEOUT


def custom_cache_key(*args, **kwargs):
    return create_cache_key('my_prefix', args[0].id, *args[1:])


def choose_timeout(self, a, b, c):
    if not isinstance(a, int):
        return DEFAULT_TIMEOUT
    return a * 100


# noinspection PyNestedDecorators
class User:
    name = 'user_name'
    prefixed_ecached = partial(ecached, prefix='USER:{self.id}', timeout=3600)
    cache_mock = None

    def __init__(self, uid, cache_mock):
        self.id = uid
        self.cache_mock = cache_mock
        User.cache_mock = cache_mock

    @ecached('dyn_timeout:{a}', timeout=choose_timeout)
    def instance_dynamic_timeout(self, a, b, c):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached()
    def instance_default_cache_key(self, a, b, c=8):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached()
    @classmethod
    def class_method_default_cache_key(cls, a, b, c=9, d='Иван'):
        return cls.cache_mock.trigger_result(a, b, c)

    @ecached_property()
    def test_property(self):
        return self.cache_mock.trigger_result('property')

    @ecached_property('manufacturer:{self.id}', 86400)
    def issue_8_test_property(self):
        return self.cache_mock.trigger_result('issue_8_property')

    @ecached('{self.id}:{a}:{b}:{c}')
    def instance_method_string(self, a, b, c=10):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached(['self.id', 'a', 'b'])
    def instance_method_list(self, a, b, c=11):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached(custom_cache_key)
    def instance_method_callable(self, a, b, c=12):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached('{self.id}:{a}:{b}', 400)
    def instance_method_timeout(self, a, b, c=13):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached('{self.id}:{a}:{b}', 500, ('tag1', 'tag2'))
    def instance_method_tags(self, a, b, c=14):
        return self.cache_mock.trigger_result(a, b, c)

    @staticmethod
    def generate_custom_tags(meta):
        """ :type meta: MetaCallable """
        if meta.has_returned_value:
            User.cache_mock.assert_called_with(meta.returned_value)

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
        return self.cache_mock.trigger_result(a, b, c)

    @ecached('{a}:{b}', tags=generate_custom_tags)
    def instance_method_custom_tags(self, a, b, c=14):
        return self.cache_mock.trigger_result(a, b, c)

    @prefixed_ecached('p1:{a}:{b}:{c}', tags=['{self.id}:tag1'])
    def instance_method_prefixed(self, a, b, c=15):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached_property('{self.id}:friends_count', timeout=100, prefix='USER_PROPERTY')
    def friends_count(self):
        self.cache_mock()
        return 15

    @ecached_property('static_key')
    def property_no_tags(self):
        self.cache_mock()
        return '42'

    @ecached(cache_key='{cls.name}:{c}')
    @classmethod
    def class_method_cache_key_string(cls, a, b, c=17):
        return cls.cache_mock.trigger_result(a, b, c)

    @ecached(('cls.name', 'a'), 500, ['tag4', 'tag5:{cls.name}'],
             prefix=lambda cls, *args, **kwargs: create_cache_key('USER', args[0], args[1]))
    @classmethod
    def class_method_full_spec(cls, a, b, c=18):
        return cls.cache_mock.trigger_result(a, b, c)

    @ecached('{hg}:{hg}:{test}', prefix=u'пользователь')
    @staticmethod
    def static_method(hg, test='abc', n=1.1):
        return User.cache_mock.trigger_result(hg, test, n)

    @ecached(tags=['ttt:{c}'], prefix='ppp:{b}')
    @staticmethod
    def static_method_default_key(a, b, c=11):
        return User.cache_mock.trigger_result(a, b, c)


# noinspection PyNestedDecorators
class AsyncUser:
    name = 'async_user_name'
    prefixed_ecached = partial(ecached, prefix='USER:{self.id}', timeout=3600)
    cache_mock = None

    def __init__(self, uid, cache_mock):
        self.id = uid
        self.cache_mock = cache_mock
        AsyncUser.cache_mock = cache_mock

    @ecached('dyn_timeout:{a}', timeout=choose_timeout)
    async def instance_dynamic_timeout(self, a, b, c):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached()
    async def instance_default_cache_key(self, a, b, c=8):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached()
    @classmethod
    async def class_method_default_cache_key(cls, a, b, c=9, d='Иван'):
        return cls.cache_mock.trigger_result(a, b, c)

    @ecached_property()
    async def test_property(self):
        return self.cache_mock.trigger_result('property')

    @ecached_property('manufacturer:{self.id}', 86400)
    async def issue_8_test_property(self):
        return self.cache_mock.trigger_result('issue_8_property')

    @ecached('{self.id}:{a}:{b}:{c}')
    async def instance_method_string(self, a, b, c=10):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached(['self.id', 'a', 'b'])
    async def instance_method_list(self, a, b, c=11):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached(custom_cache_key)
    async def instance_method_callable(self, a, b, c=12):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached('{self.id}:{a}:{b}', 400)
    async def instance_method_timeout(self, a, b, c=13):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached('{self.id}:{a}:{b}', 500, ('tag1', 'tag2'))
    async def instance_method_tags(self, a, b, c=14):
        return self.cache_mock.trigger_result(a, b, c)

    @staticmethod
    def generate_custom_tags(meta):
        """ :type meta: MetaCallable """
        if meta.has_returned_value:
            AsyncUser.cache_mock.assert_called_with(meta.returned_value)

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
    async def instance_method_meta_test(self, a, b, c=666):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached('{a}:{b}', tags=generate_custom_tags)
    async def instance_method_custom_tags(self, a, b, c=14):
        return self.cache_mock.trigger_result(a, b, c)

    @prefixed_ecached('p1:{a}:{b}:{c}', tags=['{self.id}:tag1'])
    async def instance_method_prefixed(self, a, b, c=15):
        return self.cache_mock.trigger_result(a, b, c)

    @ecached_property('{self.id}:friends_count', timeout=100, prefix='USER_PROPERTY')
    async def friends_count(self):
        self.cache_mock()
        return 15

    @ecached_property('static_key')
    async def property_no_tags(self):
        self.cache_mock()
        return '42'

    @ecached(cache_key='{cls.name}:{c}')
    @classmethod
    async def class_method_cache_key_string(cls, a, b, c=17):
        return cls.cache_mock.trigger_result(a, b, c)

    @ecached(('cls.name', 'a'), 500, ['tag4', 'tag5:{cls.name}'],
             prefix=lambda cls, *args, **kwargs: create_cache_key('USER', args[0], args[1]))
    @classmethod
    async def class_method_full_spec(cls, a, b, c=18):
        return cls.cache_mock.trigger_result(a, b, c)

    @ecached('{hg}:{hg}:{test}', prefix=u'пользователь')
    @staticmethod
    async def static_method(hg, test='abc', n=1.1):
        return AsyncUser.cache_mock.trigger_result(hg, test, n)

    @ecached(tags=['ttt:{c}'], prefix='ppp:{b}')
    @staticmethod
    async def static_method_default_key(a, b, c=11):
        return AsyncUser.cache_mock.trigger_result(a, b, c)
