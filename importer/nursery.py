from __future__ import annotations

import logging
from typing import Dict
from typing import Type

from importer.cache import ObjectCacheFacade
from importer.utils import DispatchedObjectType

logger = logging.getLogger(__name__)


class HandlerDoesNotExistError(KeyError):
    pass


class TariffObjectNursery:
    """
    Provides an interface between raw data and the Django modelling system for the tariff.

    The primary function is to take a raw python object (generally a dictionary) and convert
    it into a row in the database via the Django models.

    This layer of separation comes from the fact that often, when receiving data, the system
    will receive incomplete data objects which depend on data received later. As a result
    this "Nursery" is designed to store and look after incomplete data objects until it can
    be matched with the rest of the data and then dispatched to the database.
    """

    handlers: Dict[str, Type[BaseHandler]] = {}

    def __init__(self, cache: ObjectCacheFacade):
        self.cache = cache

    @classmethod
    def register_handler(cls, handler: Type[BaseHandler]):
        """
        Registers a handler to the TariffObjectNursery class.

        The nursery needs to be able to map all handlers against incoming data. To do this the
        nursery needs a map of handlers. This method allows handlers to register themselves so
        that they can be added to the internal nursery map - to be used when processing.
        """
        cls.handlers[handler.tag] = handler
        return handler

    def get_handler(self, tag: str):
        """
        Find a handler which matches the given tag. If one is not found throw an error.
        """
        try:
            return self.handlers[tag]
        except KeyError as e:
            raise HandlerDoesNotExistError(
                f'Handler for tag "{tag}" was expected but not found.'
            ) from e

    def submit(self, obj: DispatchedObjectType):
        """
        Entrypoint for the nursery.

        Handles whether an object can be dispatched to the database or, if some pieces of data
        are missing, cached to await new data.
        """

        handler_class = self.get_handler(obj["tag"])
        handler = handler_class(obj, self)
        result = handler.build()
        if not result:
            self._cache_object(handler)
        else:
            for key in result:
                self.cache.pop(key)

    def _cache_object(self, handler):
        self.cache.put(handler.key, handler.serialize())

    def get_handler_from_cache(self, key):
        match = self.cache.get(key)
        if match is None:
            return

        handler = self.get_handler(match["tag"])
        return handler(match, self)


def get_nursery(cache=None) -> TariffObjectNursery:
    """
    Convenience function for building a nursery object.
    """
    cache = cache or ObjectCacheFacade()
    return TariffObjectNursery(cache)
