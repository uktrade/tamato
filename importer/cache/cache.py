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
        return self.engine.get(key, default)

    def pop(self, key, default=None):
        return self.engine.pop(key, default)

    def put(self, key, obj):
        self.engine.put(key, obj)

    def keys(self):
        return self.engine.keys()

    def dump(self):
        self.engine.dump()

    def clear(self):
        self.engine.clear()
