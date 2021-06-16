from functools import cached_property

from django.db.models.fields import Field
from django.urls import NoReverseMatch
from django.urls import reverse
from polymorphic.managers import PolymorphicManager

from common.models.mixins.validity import ValidityStartMixin
from common.models.mixins.validity import ValidityStartQueryset
from common.models.records import TrackedModelQuerySet


class DescriptionQueryset(ValidityStartQueryset, TrackedModelQuerySet):
    pass


class DescriptionMixin(ValidityStartMixin):
    objects = PolymorphicManager.from_queryset(DescriptionQueryset)()

    @cached_property
    def described_object_field(self) -> Field:
        for rel, _ in self.get_relations():
            if rel.name.startswith("described_"):
                return rel
        raise TypeError(f"{self} should have a described field.")

    def get_described_object(self):
        return getattr(self, self.described_object_field.name)

    def get_url(self, action="detail"):
        kwargs = {}
        if action != "list":
            kwargs = self.get_identifying_fields()
            described_object = self.get_described_object()
            for field, value in described_object.get_identifying_fields().items():
                kwargs[
                    f"described_{described_object._meta.model_name}__{field}"
                ] = value
        try:
            return reverse(
                f"{self.get_url_pattern_name_prefix()}-ui-{action}",
                kwargs=kwargs,
            )
        except NoReverseMatch:
            return

    def __str__(self):
        return self.identifying_fields_to_string(
            identifying_fields=(
                self.described_object_field.name,
                "validity_start",
            ),
        )

    class Meta:
        abstract = True
