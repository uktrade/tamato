from importlib import import_module

import settings


class ObjectCacheFacade:
    """
    Stores objects in a cache to be fetched for later use.

    To avoid committing to a specific medium of storage this facade is being implemented
    to provide a neutral interface for getting, putting and popping object data into and
    out of storage. The only requirement is a unique hashable key for which to fetch the
    data with.

    Currently the implementation relies simply on a process level mutable dictionary.
    However in future this may be updated to use something more persistent such as
    Redis or similar.
    """

    DEFAULT_ENGINE = "importer.cache.memory.MemoryCacheEngine"

    def __init__(self, engine=None):
        if not engine:
            engine = getattr(settings, "NURSERY_CACHE_ENGINE", self.DEFAULT_ENGINE)
        engine_module_str, engine_str = engine.rsplit(".", 1)
        engine_module = import_module(engine_module_str)
        self.engine = getattr(engine_module, engine_str)()

    def get(self, key, default=None):
        """
        Gets the value for the provided key or if not present, returns the value of default

        Args:
          key: The key to return the value for
          default: The value to return if the key is not found

        Returns:
          object, either the value of the key provided or the value of the default argument provided
        """
        return self.engine.get(key, default)

    def pop(self, key, default=None):
        """
        Gets the value for the provided key and removes key from cache or if not present, returns the value of default

        Args:
          key: The key to return the value for
          default: The value to return if the key is not found

        Returns:
          object, either the value of the key provided or the value of the default argument provided
        """
        return self.engine.pop(key, default)

    def put(self, key, obj):
        """
        Stores the value for the provided key. If the key already exists, it will be overwritten

        Args:
          key: The key to store the obj against
          obj: The value to be stored against the provided key

        Returns:
          None
        """
        self.engine.put(key, obj)

    def keys(self):
        """
        Returns a list of the keys stored in cache

        Returns:
          list(str) : A list of keys for the cache
        """
        return self.engine.keys()

    def dump(self):
        """
        Present of base class compatability, does not perform any action.

        Returns:
          None
        """
        self.engine.dump()

    def clear(self):
        """
        Clears the cache, removing all keys and objects

        Returns:
          None
        """
        self.engine.clear()
