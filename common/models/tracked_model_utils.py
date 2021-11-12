from __future__ import annotations

from typing import Dict
from typing import Set
from typing import Union

from django.db.models import Field
from django.db.models import Model
from django.db.models.fields.reverse_related import ForeignObjectRel

Relation = ForeignObjectRel


def get_relations(class_: type[Model]) -> dict[Relation, type[Model]]:
    """
    Returns all the models that are related to this one.

    The link can either be stored on this model (so a one-to-one or a many- to-
    one relationship) or on the related model (so a one-to-many (reverse)
    relationship).
    """
    from common.models.trackedmodel import TrackedModel

    return {
        f: f.related_model
        for f in class_._meta.get_fields()
        if (f.many_to_one or f.one_to_one or f.one_to_many)
        and f.model == class_
        and issubclass(f.related_model, TrackedModel)
        and f.related_model is not TrackedModel
    }


def get_subrecord_relations(class_: type[Model]) -> dict[Relation, type[Model]]:
    """
    Returns a set of relations to this model's TARIC subrecords.

    E.g, a :class:`~measures.models.Measure` and a
    :class:`measures.models.MeasureComponent` are in the same "logical
    record" but are different data models because they are many-to-one.
    """
    from common.models.trackedmodel import TrackedModel

    return {
        field
        for field in class_._meta.get_fields()
        if field.one_to_many
        and field.related_model is not class_
        and issubclass(field.related_model, TrackedModel)
        and field.related_model.record_code == class_.record_code
    }


def get_models_linked_to(
    class_: type[Model],
) -> Dict[Union[Field, ForeignObjectRel], type[Model]]:
    """Returns all the models that are related to this one via a foreign key
    stored on this model (one-to-many reverse related models are not included in
    the returned results)."""
    return dict(
        (f, r)
        for f, r in get_relations(class_).items()
        if (f.many_to_one or f.one_to_one) and not f.auto_created and f.concrete
    )


def get_copyable_fields(class_: type[Model]) -> Set[Field]:
    """
    Return the set of fields that can have their values copied from one model to
    another.

    This is anything that is:
    - a native value
    - a foreign key to some other model
    """
    return {
        field
        for field in class_._meta.get_fields()
        if not any((field.many_to_many, field.one_to_many))
        and field.name not in class_.system_set_field_names
    }


def get_deferred_set_fields(class_: type[Model]) -> Set[Field]:
    """
    Returns a set of fields that can only be saved (using the
    ``instance.field.set()`` method) after the object has been saved first.

    This is any field that is a many-to-many relationship with an auto-
    generated through model.
    """
    return {
        field
        for field in class_._meta.get_fields()
        if field.many_to_many
        and hasattr(field.remote_field, "through")
        and field.remote_field.through._meta.auto_created
    }
