import asyncio
import math
import sys
from contextlib import contextmanager
from timeit import default_timer

import aioredis
from cachetools import LRUCache

from easy_cache_async import caches
from easy_cache_async.contrib import LocMemCacheBackend, RedisCacheBackend
from easy_cache_async.decorators import ecached
from tests.conftest import REDIS_CONNECTION


async def setup():
    caches['locmem'] = LocMemCacheBackend(LRUCache(maxsize=1000))

    redis = await aioredis.create_redis(REDIS_CONNECTION)
    caches['redis'] = RedisCacheBackend(redis)


async def teardown():
    await caches['redis'].close()


def ratio(a, b):
    if a > b:
        return a / b, 1
    elif a < b:
        return 1, b / a
    else:
        return 1, 1


class Stopwatch(object):

    def __init__(self, name):
        self.name = name
        self.t0 = default_timer()
        self.laps = []

    def __str__(self):
        m = self.mean()
        d = self.stddev()
        a = self.median()
        fmt = u'%-37s: mean=%0.5f, median=%0.5f, stddev=%0.5f, n=%3d, snr=%8.5f:%8.5f'
        return fmt % ((self.name, m, a, d, len(self.laps)) + ratio(m, d))

    def mean(self):
        return sum(self.laps) / len(self.laps)

    def median(self):
        return sorted(self.laps)[int(len(self.laps) / 2)]

    def stddev(self):
        mean = self.mean()
        return math.sqrt(sum((lap - mean) ** 2 for lap in self.laps) / len(self.laps))

    def total(self):
        return default_timer() - self.t0

    def reset(self):
        self.t0 = default_timer()
        self.laps = []

    @contextmanager
    def timing(self):
        t0 = default_timer()
        try:
            yield
        finally:
            te = default_timer()
            self.laps.append(te - t0)


c = 0


def time_consuming_operation():
    global c
    c += 1
    a = sum(range(1000000))
    return str(a)


async def test_no_cache():
    return time_consuming_operation()


@ecached(cache_alias='locmem')
async def test_locmem_cache():
    return time_consuming_operation()


@ecached(cache_alias='redis')
async def test_redis_cache():
    return time_consuming_operation()


@ecached(cache_alias='locmem', tags=['tag1', 'tag2'])
async def test_locmem_cache_tags():
    return time_consuming_operation()


@ecached(cache_alias='redis', tags=['tag1', 'tag2'])
async def test_redis_cache_tags():
    return time_consuming_operation()


async def main():
    await setup()

    print('=======', 'Python:', sys.version.replace('\n', ''), '=======')

    global c
    n = 100

    benchmarks = (
        (test_no_cache, n),
        (test_locmem_cache, 1),
        (test_locmem_cache_tags, 1),
        (test_redis_cache, 1),
        (test_redis_cache_tags, 1),
    )

    async def cleanup(function):
        if hasattr(function, 'invalidate_cache_by_key'):
            await function.invalidate_cache_by_key()
        if hasattr(function, 'invalidate_cache_by_tags'):
            await function.invalidate_cache_by_tags()

    for method, count in benchmarks:
        sw1 = Stopwatch('[cleanup] ' + method.__name__)
        await cleanup(method)
        c = 0

        for _ in range(n):
            with sw1.timing():
                await method()
            await cleanup(method)

        assert c == n, c
        print(sw1)

        sw2 = Stopwatch('[ normal] ' + method.__name__)
        await cleanup(method)
        c = 0

        for _ in range(n):
            # skip first time
            if _ == 0:
                await method()
                continue
            with sw2.timing():
                await method()

        assert c == count, c
        print(sw2)
        print('mean diff: {:.3} %, median diff: {:.3} %'.format(
            float(sw2.mean()) / sw1.mean() * 100,
            float(sw2.median()) / sw1.median() * 100,
        ))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_until_complete(teardown())
