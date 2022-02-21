from typing import Any
from typing import Dict
from typing import Tuple

from django.db.models import Model
from django.db.models.fields import Field
from polymorphic.managers import PolymorphicManager


class TrackedModelManager(PolymorphicManager):
    """
    Fixes reverse relations so that always return correct results for versioned
    models.

    For why, see ADR `15. Make reverse relations aware of versions`_.

    This mixin swaps out the foreign keys used by the RelatedManager for
    querying and replaces them with the version group of the instance. The
    apporach is to take over control of the `core_filters` attribute used in
    django/db/models/fields/related_descriptors.py.

    The attribute is only set in two places – either once for a RelatedManager
    or (in the case of a many-to-many relation) updated in a loop, but the loop
    is only dependent on context provided by the relation itself. Hence it is
    possible to define a property override for `core_filters` that will always
    return the correct result, and ignore anything that it set to the property.
    """

    instance: Model
    """This is the model we are trying to find related objects to – e.g. the
    `parent` that we are calling `descriptions` on in the example in the ADR."""

    field: Field
    """
    This is the foreign key field on the remote model – e.g. the
    `described_object` field of the `Description` model that links back to
    `Parent` objects in the above example.

    This will be set if this is a one-to-many relationship and this Manager is
    being used as a RelatedManager. If this is a many-to-many relationship this
    Manager is a ManyRelatedManager and this attribute is not present.
    """

    def get_filter_for_relationship(self, model) -> Tuple[str, Any]:
        """Use the passed object's version group for querying if it has one,
        otherwise resolve the foreign key normally."""
        if hasattr(model, "version_group"):
            return "__version_group", model.version_group
        else:
            return "", model

    def get_core_filters(self) -> Dict[str, Any]:
        """
        Returns a dictionary of filters used to find related objects.

        The logic duplicates RelatedManager and ManyRelatedManager, but for the
        former uses version groups instead of foreign keys.
        """

        if hasattr(self, "field"):
            # RelatedManager: find all of the remote objects that refer to this
            # instance by querying on the field name on the remote objects.
            suffix, object = self.get_filter_for_relationship(self.instance)
            return {f"{self.field.name}{suffix}": object}
        else:
            # ManyRelatedManager: this is a many-to-many relationship with an
            # auto-generated through model. The auto-generated model does not
            # take part in the TrackedModel system – hence each version of the
            # many-to-many models needs an independent set of links, otherwise
            # it wouldn't be possible for the links to be updated. The
            # implementation is the same as the default and it is up to the code
            # that creates new versions to duplicate the many-to-many links.
            return {
                f"{self.query_field_name}__{rh_field.attname}": getattr(
                    self.instance,
                    rh_field.attname,
                )
                for _, rh_field in self.source_field.related_fields
            }

    def set_core_filters(self, value: Dict[str, Model]) -> None:
        """Used by Django internal code – we are ignoring what it sets and
        instead using our own filters."""

    core_filters = property(get_core_filters, set_core_filters)


class CurrentTrackedModelManager(TrackedModelManager):
    def get_queryset(self):
        return super().get_queryset().current()
