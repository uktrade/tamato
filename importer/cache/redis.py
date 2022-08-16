from django.conf import settings
from django.core.cache import cache

from importer.cache.base import BaseEngine


def prefix_key_decorator(func):
    def wrapped_func(self, key, *args, **kwargs):
        prefix = getattr(settings, "IMPORTER_CACHE_PREFIX", "__IMPORTER_CACHE")
        if not key.startswith(prefix):
            key = f"{prefix}__{key}"
        return func(self, key, *args, **kwargs)

    return wrapped_func


class RedisCacheEngine(BaseEngine):
    CACHE_PREFIX = "__IMPORTER_CACHE"

    @prefix_key_decorator
    def get(self, key, default=None):
        """
        Gets the value for the provided key or if not present, returns the value
        of default.

        Args:
          key: The key to return the value for
          default: The value to return if the key is not found

        Returns:
          object, either the value of the key provided or the value of the default argument provided
        """
        return cache.get(key, default)

    @prefix_key_decorator
    def pop(self, key, default=None):
        """
        Gets the value for the provided key and removes key from cache or if not
        present, returns the value of default.

        Args:
          key: The key to return the value for
          default: The value to return if the key is not found

        Returns:
          object, either the value of the key provided or the value of the default argument provided
        """
        result = cache.get(key)

        if result is None:
            result = default

        cache.delete(key)

        return result

    @prefix_key_decorator
    def put(self, key, obj):
        """
        Stores the value for the provided key. If the key already exists, it
        will be overwritten. There will be no redis timeout associated with this
        key.

        Args:
          key: The key to store the obj against
          obj: The value to be stored against the provided key

        Returns:
          None
        """
        cache.set(key, obj, timeout=None)

    def keys(self):
        """
        Returns a list of the keys stored in cache.

        Returns:
          list(str) : A list of keys for the cache
        """
        prefix = getattr(settings, "IMPORTER_CACHE_PREFIX", "__IMPORTER_CACHE")
        return cache.keys(f"{prefix}*")

    def dump(self):
        """
        Present of base class compatability, does not perform any action.

        Returns:
          None
        """

    def clear(self):
        """
        Clears the cache, removing all keys and objects.

        Returns:
          None
        """
        prefix = getattr(settings, "IMPORTER_CACHE_PREFIX", "__IMPORTER_CACHE")
        cache.delete(f"{prefix}*")
