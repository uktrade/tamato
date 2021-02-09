import pickle
from pathlib import Path

from importer.cache.base import BaseEngine


class PickleCacheEngine(BaseEngine):
    CACHE = {}

    CACHE_FILE = Path("_dumped_cache.pkl")

    def __init__(self):
        if not self.CACHE_FILE.exists():
            return

        with open(self.CACHE_FILE, "rb") as dump_file:
            dumped_cache = pickle.load(dump_file)

            if dumped_cache:
                self.CACHE.update(dumped_cache)

    def get(self, key, default=None):
        return self.CACHE.get(key, default)

    def pop(self, key, default=None):
        return self.CACHE.pop(key, default)

    def put(self, key, obj):
        self.CACHE[key] = obj

    def keys(self):
        return self.CACHE.keys()

    def dump(self):
        with open(self.CACHE_FILE, "wb") as dump_file:
            pickle.dump(self.CACHE, dump_file)

    def clear(self):
        self.CACHE.clear()
