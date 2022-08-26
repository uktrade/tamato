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
        return cache.get(key, default)

    @prefix_key_decorator
    def pop(self, key, default=None):
        result = cache.get(key)

        if result is None:
            result = default

        cache.delete(key)

        return result

    @prefix_key_decorator
    def put(self, key, obj):
        cache.set(key, obj, timeout=None)

    def keys(self):
        prefix = getattr(settings, "IMPORTER_CACHE_PREFIX", "__IMPORTER_CACHE")
        return cache.keys(f"{prefix}*")

    def dump(self):
        pass

    def clear(self):
        prefix = getattr(settings, "IMPORTER_CACHE_PREFIX", "__IMPORTER_CACHE")
        cache.delete(f"{prefix}*")
