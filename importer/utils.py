from __future__ import annotations

from hashlib import sha256
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import TypedDict

from django.db.models.query_utils import DeferredAttribute

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


def build_dependency_tree(use_subrecord_codes: bool = False) -> Dict[str, Set[str]]:
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
    def _get_record_codes(record: TrackedModel) -> List[str]:
        key = record.record_code

        if use_subrecord_codes is False:
            return [key]

        subrecord_code = record.subrecord_code

        if isinstance(subrecord_code, str):
            return [f"{key}{subrecord_code}"]

        if isinstance(subrecord_code, DeferredAttribute):
            return [
                f"{key}{code}"
                for code, _ in subrecord_code.field.choices
            ]

        return []

    dependency_map = {}

    record_codes = {
        code
        for subclass in TrackedModel.__subclasses__()
        for code in _get_record_codes(subclass)
    }

    for subclass in TrackedModel.__subclasses__():
        if subclass.__name__[:4] == "Test":
            continue

        for record_code in _get_record_codes(subclass):
            if record_code not in dependency_map:
                dependency_map[record_code] = set()

            for _, relation in subclass.get_relations():
                relation_codes = _get_record_codes(relation)

                for relation_code in relation_codes:
                    if (
                        relation_code != record_code
                        and relation_code in record_codes
                    ):
                        dependency_map[record_code].add(relation_code)

    return dependency_map


dependency_tree = build_dependency_tree()
