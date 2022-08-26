from importer.cache.base import BaseEngine


class MemoryCacheEngine(BaseEngine):
    CACHE = {}

    def get(self, key, default=None):
        return self.CACHE.get(key, default)

    def pop(self, key, default=None):
        return self.CACHE.pop(key, default)

    def put(self, key, obj):
        self.CACHE[key] = obj

    def keys(self):
        return self.CACHE.keys()

    def dump(self):
        pass

    def clear(self):
        self.CACHE.clear()
