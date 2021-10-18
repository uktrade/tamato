from __future__ import annotations

from typing import Any
from typing import TypeVar

from django.db.models import Field
from django.db.models import Model
from django.db.models.fields.reverse_related import ForeignObjectRel

TrackedModel = TypeVar("TrackedModel")


Relation = Field[Any, Any] | ForeignObjectRel


def get_relations(class_: type[Model]) -> dict[Relation, type[Model]]:
    """
    Returns all the models that are related to this one.

    The link can either be stored on this model (so a one-to-one or a many- to-
    one relationship) or on the related model (so a one-to-many (reverse)
    relationship).
    """
    return {
        f: f.related_model
        for f in class_._meta.get_fields()
        if (f.many_to_one or f.one_to_one or f.one_to_many)
        and f.model == class_
        and issubclass(f.related_model, TrackedModel)
        and f.related_model is not TrackedModel
    }
