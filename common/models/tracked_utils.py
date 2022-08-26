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


def get_field_hashable_string(value):
    """
    Given a field return a hashable string, containing the fields type and
    value, ensuring uniqueness across types.

    For fields that are TrackedModels, delegate to their content_hash method.
    For non TrackedModels return a combination of type and value.
    """
    from common.models.trackedmodel import TrackedModel

    value_type = type(value)
    if isinstance(value, TrackedModel):
        # For TrackedModel fields use their content_hash, the type is still included as a debugging aid.
        value_hash = value.content_hash().hexdigest()
        return (
            f"{value_type.__module__}:{value_type.__name__}.content_hash={value_hash}"
        )

    return f"{value_type.__module__}:{value_type.__name__}={value}"


class NotPresent:
    # Sentinel value for fields that are not present.
    pass


def get_field_hashable_strings(instance, fields):
    """
    Given a model instance, return a dict of {field names: hashable string},

    This calls `get_field_hashable_string` to generate strings unique to the type and value of the fields.

    :param instance: The model instance to generate hashes for.
    :param fields: The fields to get use in the hash.
    :return:  Dictionary of {field_name: hash}
    """
    return {
        field.name: get_field_hashable_string(getattr(instance, field.name, NotPresent))
        for field in fields
    }
