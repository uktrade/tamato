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

    CACHE = {}

    def get(self, key, default=None):
        return self.CACHE.get(key, default)

    def pop(self, key, default=None):
        return self.CACHE.pop(key, default)

    def put(self, key, obj):
        self.CACHE[key] = obj
