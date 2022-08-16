from abc import ABC, abstractmethod


class BaseEngine(ABC):
    @abstractmethod
    def get(self, key, default=None):

        pass

    @abstractmethod
    def pop(self, key, default=None):
        pass

    @abstractmethod
    def put(self, key, obj):
        pass

    @abstractmethod
    def keys(self):
        pass

    @abstractmethod
    def dump(self):
        pass

    @abstractmethod
    def clear(self):
        pass
