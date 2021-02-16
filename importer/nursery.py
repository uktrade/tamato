from __future__ import annotations

import logging
from itertools import chain
from typing import Dict
from typing import Iterable
from typing import Tuple
from typing import Type

from django.core.cache import cache

from commodities.exceptions import InvalidIndentError
from common.models import TrackedModel
from importer.cache import ObjectCacheFacade
from importer.utils import DispatchedObjectType
from importer.utils import generate_key

logger = logging.getLogger(__name__)


class HandlerDoesNotExistError(KeyError):
    pass


class TariffObjectNursery:
    """
    Provides an interface between raw data and the Django modelling system for
    the tariff.

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
        Find a handler which matches the given tag.

        If one is not found throw an error.
        """
        try:
            return self.handlers[tag]
        except KeyError as e:
            raise HandlerDoesNotExistError(
                f'Handler for tag "{tag}" was expected but not found.',
            ) from e

    def submit(self, obj: DispatchedObjectType):
        """
        Entrypoint for the nursery.

        Handles whether an object can be dispatched to the database or, if some
        pieces of data are missing, cached to await new data.
        """
        handler_class = self.get_handler(obj["tag"])
        handler = handler_class(obj, self)
        try:
            result = handler.build()
            if not result:
                self._cache_handler(handler)
            else:
                for key in result:
                    self.cache.pop(key)
        except InvalidIndentError:
            logger.warning("Parent not found for %s, caching indent", obj)
            self._cache_handler(handler)
        except Exception:
            logger.error("obj errored: %s", obj)
            logger.info("cache size: %d", len(self.cache.keys()))
            self.clear_cache()
            self.cache.dump()
            raise

    def _cache_handler(self, handler):
        self.cache.put(handler.key, handler.serialize())

    def clear_cache(self, repeats: int = 2):
        """
        Iterate over the cache and handle any objects which can be resolved.

        As the importer runs many objects are created before their proper
        relationships can be found. In some cases these will be cleared by
        interdependent handlers. However in some cases (foreign key links)
        the objects are left dangling in the cache.

        This method runs through the cache and tries to resolve all objects
        that it can. As some of the objects often depend on other objects
        which are also in the cache, but appear later, this method runs
        recursively based on the `repeats` argument
        """
        for key in list(self.cache.keys()):
            handler = self.get_handler_from_cache(key)
            try:
                if handler is None:
                    self.cache.pop(key)
                    continue
                result = handler.build()
                if not result:
                    self._cache_handler(handler)
                else:
                    for key in result:
                        self.cache.pop(key)
            except InvalidIndentError:
                self._cache_handler(handler)

        repeats -= 1
        if repeats <= 0:
            if self.cache.keys():
                logger.warning(
                    "cache not cleared, %d records remaining",
                    len(self.cache.keys()),
                )
            return

        self.clear_cache(repeats)

    def get_handler_from_cache(self, key):
        match = self.cache.get(key)
        if match is None:
            return

        handler = self.get_handler(match["tag"])
        return handler(match, self)

    def get_handler_link_fields(self, model, link_fields=None):
        """
        Find all the unique link fields for a given model.

        This gives all the combinations of fields used to identify a model.
        """
        link_fields = link_fields or set()
        for handler in filter(lambda x: x.links, self.handlers.values()):
            for link in filter(lambda x: x["model"] == model, handler.links):
                link_fields.add(
                    tuple(
                        sorted(
                            link.get("identifying_fields", model.identifying_fields),
                        ),
                    ),
                )
        return link_fields

    def cache_current_instances(self):
        """Take all current instances of all TrackedModels in the data and cache
        them."""
        models = {handler.model for handler in self.handlers.values()}

        for model in models:
            logger.info("Caching all current instances of %s", model)
            link_fields = self.get_handler_link_fields(model)
            if not link_fields:
                continue

            values_list = set(chain.from_iterable(link_fields))
            values_list.add("pk")

            for obj in model.objects.current().select_related():
                self.cache_object(obj)

    def cache_object(self, obj: TrackedModel):
        """
        Caches an objects primary key and model name in the cache.

        Key is generated based on the model name and the identifying fields used
        to find it.
        """
        model = obj.__class__
        link_fields = self.get_handler_link_fields(model)

        for identifying_fields in link_fields:
            cache_key = self.generate_cache_key(
                model,
                identifying_fields,
                obj.get_identifying_fields(identifying_fields),
            )
            cache.set(cache_key, (obj.pk, model.__name__), timeout=None)

    def remove_object_from_cache(self, obj: TrackedModel):
        """
        Removes an object from the importer cache. If an object has to be
        deleted (generally done in dev only) then it is problematic to keep the
        ID in the cache as well.

        Key is generated based on the model name and the identifying fields used
        to find it.
        """
        model = obj.__class__
        link_fields = self.get_handler_link_fields(model)

        for identifying_fields in link_fields:
            cache_key = self.generate_cache_key(
                model,
                identifying_fields,
                obj.get_identifying_fields(identifying_fields),
            )
            cache.delete(cache_key)

    @classmethod
    def generate_cache_key(
        cls,
        model: Type[TrackedModel],
        identifying_fields: Iterable,
        obj: dict,
    ) -> str:
        """Generate a cache key based on the model name and the identifying
        values used to find it."""
        return "object_cache_" + generate_key(model.__name__, identifying_fields, obj)

    @classmethod
    def get_obj_from_cache(
        cls,
        model: Type[TrackedModel],
        identifying_fields: Iterable,
        obj: dict,
    ) -> Tuple[int, str]:
        """Fetches an object PK and model name from the cache if it exists."""
        key = cls.generate_cache_key(model, identifying_fields, obj)
        return cache.get(key)


def get_nursery(object_cache=None) -> TariffObjectNursery:
    """Convenience function for building a nursery object."""
    object_cache = object_cache or ObjectCacheFacade()
    return TariffObjectNursery(object_cache)
