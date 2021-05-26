from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from hashlib import sha256
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Set
from typing import TypedDict

from common.models.records import TrackedModel


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
    tag: str,
    identifying_fields: Iterable[str],
    data: Dict[str, Any],
) -> str:
    """
    Generate a unique hash key for each object.

    The identifying fields are the primary input for the hash however,
    as these are likely to be duplicated across all the interdependent
    objects - as well as a possibility , the serializer class and "name" have been
    """
    hash_input = tag
    for key in identifying_fields:
        hash_input += str(data[key])

    return sha256(hash_input.encode()).hexdigest()


@lru_cache
def get_record_code(model: TrackedModel):
    from importer.taric import RecordParser

    try:
        handler = RecordParser.serializer_map[model]
        return handler.xml_model.record_code
    except KeyError:
        return None


@lru_cache(maxsize=1)
def build_dependency_tree() -> Dict[str, Set[str]]:
    """
    Build a dependency tree of all the TrackedModel subclasses mapped by record
    code.

    The return value is a dictionary, mapped by record code, where the mapped values
    are sets listing all the other record codes the mapped record code depends on.

    A dependency is defined as any foreign key relationship to another record code.
    An example output is given below.

    .. code:: python

        {
            "220": {"215", "210"},
        }
    """

    dependency_map = defaultdict(set)

    record_codes = {
        subclass: get_record_code(subclass)
        for subclass in TrackedModel.__subclasses__()
        if get_record_code(subclass) is not None
    }

    for subclass in record_codes.keys():
        subclass_record_code = record_codes[subclass]
        for _, relation in subclass.get_relations():
            relation_record_code = get_record_code(relation)
            if (
                relation_record_code != subclass_record_code
                and relation_record_code in record_codes.values()
            ):
                dependency_map[subclass_record_code].add(relation_record_code)

    return dict(dependency_map)
