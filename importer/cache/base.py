class BaseEngine:
    def get(self, key, default=None):
        raise NotImplementedError

    def pop(self, key, default=None):
        raise NotImplementedError

    def put(self, key, obj):
        raise NotImplementedError

    def keys(self):
        raise NotImplementedError

    def dump(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError
