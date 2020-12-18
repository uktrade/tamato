from hashlib import sha256
from typing import Any
from typing import Dict
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
        - transaction_id - the transaction to attach the object to.
    """

    data: dict
    tag: str
    transaction_id: int


def generate_key(
    tag: str, identifying_fields: Iterable[str], data: Dict[str, Any]
) -> bytes:
    """
    Generate a unique hash key for each object.

    The identifying fields are the primary input for the hash however,
    as these are likely to be duplicated across all the interdependent
    objects - as well as a possibility , the serializer class and "name" have been
    """
    hash_input = tag
    for key in identifying_fields:
        hash_input += str(data[key])

    return sha256(hash_input.encode()).digest()
