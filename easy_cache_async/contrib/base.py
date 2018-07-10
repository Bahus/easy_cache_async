import json
from abc import ABC, abstractmethod

from ..core import DEFAULT_TIMEOUT, NOT_FOUND, create_cache_key
from ..utils import force_binary, force_text


class BaseCacheBackend(ABC):

    def __init__(self, **options):
        self.prefix = options.get('prefix')
        self.make_key = options.get('make_key', self.default_make_key)
        self.timeout = options.get('timeout')
        self.options = options

    def default_make_key(self, key):
        if not self.prefix:
            return key
        return create_cache_key(self.prefix, key)

    def make_keys(self, keys):
        return [self.make_key(key) for key in keys]

    def make_timeout(self, timeout):
        if timeout is DEFAULT_TIMEOUT:
            return self.timeout
        return timeout

    @abstractmethod
    async def get(self, key, default=NOT_FOUND):
        """
            :type key: str | basestring
            :rtype Any | None
        """
        pass

    @abstractmethod
    async def get_many(self, keys):
        """
            :type keys: list | tuple
            :rtype dict:
        """
        pass

    @abstractmethod
    async def set(self, key, value, timeout=DEFAULT_TIMEOUT):
        """
            :type key: str | basestring
        """
        pass

    @abstractmethod
    async def set_many(self, data_dict, timeout=DEFAULT_TIMEOUT):
        """
            :type data_dict: dict
        """
        pass

    @abstractmethod
    async def delete(self, key):
        """
            :type key: str | basestring
        """
        pass


class SerializerMixin:
    """Interface to support data serialization"""

    def __init__(self, **options):
        self.serializer = options.pop('serializer', json)
        # noinspection PyArgumentList
        super().__init__(**options)

    def load_value(self, value):
        if value is None:
            return value

        value = force_text(value)
        return self.serializer.loads(value)

    def dump_value(self, value):
        return force_binary(self.serializer.dumps(value))
