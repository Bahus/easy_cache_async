from collections import OrderedDict
from functools import partial

import pytest
import random
from unittest.mock import call, Mock

from easy_cache_async import (
    ecached,
    ecached_property,
    set_global_cache_instance,
    meta_accepted,
)
from easy_cache_async import MetaCallable
from easy_cache_async.contrib.dummy import DummyCacheInstance
from easy_cache_async.core import NOT_FOUND, create_cache_key

from .tools import CacheMock, AsyncMock
from .conftest import create_locmem, create_locmem_lru, create_redis

cache_mock = CacheMock()


class Player:
    key = 'players-cache'

    def __init__(self, name, age, rating=None):
        self.name = name
        self.age = age
        self.rating = rating

    @staticmethod
    @meta_accepted
    def _generate_tags(meta: MetaCallable):
        if meta.has_returned_value:
            return [p.name for p in meta.returned_value]
        return None

    @ecached('{self.name}-{self.age}-{limit}', prefix='{self.key}', tags=_generate_tags)
    def get_friends(self, limit=None):
        count = limit or random.randint(1, 20)
        result = []

        for i in range(count):
            result.append(
                Player(
                    'name_{0}'.format(i),
                    age=18 + i,
                    rating=random.randint(0, i),
                )
            )

        cache_mock.trigger_result('get_friends')
        return result

    @ecached_property('{self.name}', timeout=100)
    def friends_count(self):
        cache_mock.trigger_result('friends_count')
        return 10

    def __str__(self) -> str:
        return '{self.name}-{self.age}-{self.rating}'.format(self=self)


@pytest.fixture
def player():
    return Player(
        name='default player',
        age=33,
        rating=100,
    )


@pytest.mark.usefixtures('setup')
@pytest.mark.asyncio
class TestDummyCacheInstance:

    # noinspection PyAttributeOutsideInit
    @pytest.fixture
    def setup(self):
        global cache_mock

        self.cache_mock = cache_mock  # type: CacheMock
        self.cache_mock.reset_mock()

        cache_instance = DummyCacheInstance()
        set_global_cache_instance(cache_instance)

    async def test_result_is_not_cached(self, player: Player):
        await player.get_friends()
        await player.get_friends()

        # no cache
        self.cache_mock.assert_has_calls([
            call('get_friends'),
            call('get_friends'),
        ])

        self.cache_mock.reset_mock()

        assert await player.friends_count == 10
        assert await player.friends_count == 10

        # no cache
        self.cache_mock.assert_has_calls([
            call('friends_count'),
            call('friends_count'),
        ])

    async def test_all_dummy_methods_were_called(self, player: Player):
        dummy_methods = OrderedDict([
            ('delete', None),
            ('get', NOT_FOUND),
            ('get_many', {}),
            ('set', None),
            ('set_many', None),
        ])

        cache_instance = Mock(spec=DummyCacheInstance)

        for method, value in dummy_methods.items():
            setattr(cache_instance, method, AsyncMock(return_value=value))

        set_global_cache_instance(cache_instance)

        await player.get_friends()
        await player.get_friends.invalidate_cache_by_key('some-cache-key')
        assert await player.friends_count == 10

        for method, _ in dummy_methods.items():
            assert getattr(cache_instance, method).call_args_list


@pytest.fixture(
    params=[
        create_locmem,
        create_locmem_lru,
        create_redis,
    ],
    ids=[
        'locmem',
        'locmem_lru',
        'redis',
    ],
)
def cache_instance_factory(event_loop, request):
    return partial(request.param, event_loop, request)


@pytest.mark.asyncio
class TestBaseInstanceInterface:

    async def test_timeout(self, cache_instance_factory):
        # no timeout
        cache_instance = await cache_instance_factory()
        await cache_instance.set('key1', 'value1')
        assert await cache_instance.get_timeout('key1') is None

        # class timeout
        global_timeout = 10
        cache_instance = await cache_instance_factory(timeout=global_timeout)
        await cache_instance.set('key2', 'value2')
        assert await cache_instance.get_timeout('key2') == global_timeout

        # method timeout
        local_timeout = 20
        await cache_instance.set('key3', 'value3', timeout=local_timeout)
        assert await cache_instance.get_timeout('key3') == local_timeout

    async def test_prefix(self, cache_instance_factory):
        simple_prefix = 'project1'
        cache_instance = await cache_instance_factory(prefix=simple_prefix)

        await cache_instance.set('key1', 'value1')
        assert await cache_instance.get('key1') == 'value1'

        keys = await cache_instance.get_all_keys()
        assert len(keys) == 1
        assert create_cache_key(simple_prefix, 'key1') == keys[0]
        await cache_instance.clear()

        cache_data = {
            'key2': 'value2',
            'key3': 'value3',
        }

        await cache_instance.set_many(cache_data)

        keys = await cache_instance.get_all_keys()
        assert len(keys) == len(cache_data)
        assert (
            sorted([create_cache_key(simple_prefix, key) for key in cache_data])
            ==
            sorted(keys)
        )

        data = await cache_instance.get_many(cache_data.keys())
        assert data == cache_data

    async def test_make_key(self, cache_instance_factory):

        def key_maker(key):
            return create_cache_key('hello', 'world', key)

        # prefix will not be used
        simple_prefix = 'project2'
        cache_instance = await cache_instance_factory(
            prefix=simple_prefix,
            make_key=key_maker,
        )

        await cache_instance.set('key1', 'value1')
        await cache_instance.set('key2', 'value2')

        keys = await cache_instance.get_all_keys()
        assert len(keys) == 2
        assert (
            sorted([key_maker('key1'), key_maker('key2')])
            ==
            sorted(keys)
        )
