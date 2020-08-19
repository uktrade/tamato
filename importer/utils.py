from hashlib import sha256
from typing import Iterable
from typing import Optional
from typing import TypedDict

from common.models import TrackedModel


class LinksType(TypedDict):
    """
    A type defining the interface between a handler and its links.

    This constitutes:

        - identifying_fields - for the fields which are specific identifiers for the link.
        - model - for the model being linked to.
        - name - for the name of the link on the object being made.
        - optional - whether this link is nullable.
    """

    identifying_fields: Optional[Iterable[str]]
    model: TrackedModel
    name: str
    optional: bool


class DispatchedObjectType(TypedDict):
    """
    A type defining the interface expected for any object passed to the
    TariffObjectNursery.

    This constitutes:
        - data - a dictionary with objects data
        - tag - the type of record it reflects
        - workbasket_id - the workbasket to attach the object to.
    """

    data: dict
    tag: str
    workbasket_id: int


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


def generate_key(tag: str, identifying_fields: Iterable[str], data: dict) -> bytes:
    """
    Generate a unique hash key for each object.

    The identifying fields are the primary input for the hash however,
    as these are likely to be duplicated across all the interdependent
    objects - as well as a possibility , the serializer class and "name" have been
    """
    hash_input = tag
    for key in identifying_fields:
        hash_input += data[key]

    return sha256(hash_input.encode()).digest()
