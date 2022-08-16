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
        """
        Gets the value for the provided key or if not present, returns the value of default

        Args:
          key: The key to return the value for
          default: The value to return if the key is not found

        Returns:
          object, either the value of the key provided or the value of the default argument provided
        """
        return self.CACHE.get(key, default)

    def pop(self, key, default=None):
        """
        Gets the value for the provided key and removes key from cache or if not present, returns the value of default

        Args:
          key: The key to return the value for
          default: The value to return if the key is not found

        Returns:
          object, either the value of the key provided or the value of the default argument provided
        """
        return self.CACHE.pop(key, default)

    def put(self, key, obj):
        """
        Stores the value for the provided key. If the key already exists, it will be overwritten

        Args:
          key: The key to store the obj against
          obj: The value to be stored against the provided key

        Returns:
          None
        """
        self.CACHE[key] = obj

    def keys(self):
        """
        Returns a list of the keys stored in cache

        Returns:
          list(str) : A list of keys for the cache
        """
        return self.CACHE.keys()

    def dump(self):
        """
        Writes the cache to a pickle file (default _dumped_cache.pkl)

        Returns:
          None
        """
        with open(self.CACHE_FILE, "wb") as dump_file:
            pickle.dump(self.CACHE, dump_file)

    def clear(self):
        """
        Clears the cache, removing all keys and objects

        Returns:
          None
        """
        self.CACHE.clear()
