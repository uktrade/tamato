from django.db.models.fields import Field
from django.urls import NoReverseMatch
from django.urls import reverse
from polymorphic.managers import PolymorphicManager

from common.business_rules import NoBlankDescription
from common.business_rules import UpdateValidity
from common.models.mixins.validity import ValidityStartMixin
from common.models.mixins.validity import ValidityStartQueryset
from common.models.records import TrackedModelQuerySet
from common.util import classproperty


class DescriptionQueryset(ValidityStartQueryset, TrackedModelQuerySet):
    pass


class DescriptionMixin(ValidityStartMixin):
    objects = PolymorphicManager.from_queryset(DescriptionQueryset)()

    business_rules = (
        NoBlankDescription,
        UpdateValidity,
    )

    @classproperty
    def described_object_field(cls) -> Field:
        for rel in cls.relations.keys():
            if rel.name.startswith("described_"):
                return rel
        raise TypeError(f"{cls} should have a described field.")

    @classproperty
    def validity_over(cls):
        return cls.described_object_field.name

    def get_described_object(self):
        return getattr(self, self.described_object_field.name)

    def get_url(self, action="detail"):
        kwargs = {}
        if action != "list":
            kwargs = self.get_identifying_fields()
            described_object = self.get_described_object()
            for field, value in described_object.get_identifying_fields().items():
                kwargs[f"{self.described_object_field.name}__{field}"] = value
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
