"""
    Tests configuration options
"""
import os
import pytest

# forced to be enabled in tests, since we need to change cache instance type dynamically
os.environ['EASY_CACHE_ASYNC_LAZY_MODE_ENABLE'] = 'yes'

# if enabled, you'll see additional logging from cache classes
DEBUG = os.environ.get('EASY_CACHE_ASYNC_DEBUG') == 'yes'

# host:port used in redis-live tests, see readme for docker commands
REDIS_CONNECTION = os.environ.get('EASY_CACHE_ASYNC_REDIS_HOST', '0.0.0.0:6379').split(':')


if DEBUG:
    import logging
    logging.basicConfig(level=logging.DEBUG)


def create_locmem(event_loop, request):
    from .proxies import LocMemCacheProxy
    return LocMemCacheProxy.create(maxsize=10)


def create_locmem_lru(event_loop, request):
    from .proxies import LocMemCacheProxy
    from cachetools import LRUCache
    return LocMemCacheProxy.create(cache_class=LRUCache, maxsize=10)


def create_redis(event_loop, request):
    from .proxies import RedisCacheProxy
    redis_proxy = event_loop.run_until_complete(RedisCacheProxy.create())

    def teardown_redis():
        redis_proxy.cache_instance.client.quit()
        event_loop.run_until_complete(redis_proxy.cache_instance.client.wait_closed())

    request.addfinalizer(teardown_redis)
    return redis_proxy


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
def cache_proxy(event_loop, request):
    """Creates proxy with additional functionality for
    every provided cache backend.
    """
    cache_factory = request.param
    cache_proxy_instance = cache_factory(event_loop, request)

    yield cache_proxy_instance

    event_loop.run_until_complete(cache_proxy_instance.clear())

