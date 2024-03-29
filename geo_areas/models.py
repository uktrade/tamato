from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models import CheckConstraint
from django.db.models import Max
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from polymorphic.managers import PolymorphicManager

from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models.mixins.description import DescribedMixin
from common.models.mixins.description import DescriptionMixin
from common.models.mixins.validity import ValidityMixin
from common.models.tracked_qs import TrackedModelQuerySet
from common.models.trackedmodel import TrackedModel
from common.models.utils import GetTabURLMixin
from geo_areas import business_rules
from geo_areas.validators import AreaCode
from geo_areas.validators import area_id_validator
from measures import business_rules as measures_business_rules
from quotas import business_rules as quotas_business_rules


class GeographicalAreaQuerySet(TrackedModelQuerySet):
    def erga_omnes(self):
        return self.filter(area_code=AreaCode.GROUP, area_id=1011)

    def with_latest_description(qs):
        """
        Returns a GeographicalArea queryset annotated with the latest result of
        a GeographicalAreaDescription subquery's description value, linking
        these two queries on version_group field.

        Where an area has multiple current descriptions, the description with
        the latest validity_start date is used.
        """
        current_descriptions = (
            GeographicalAreaDescription.objects.current()
            .filter(described_geographicalarea__version_group=OuterRef("version_group"))
            .order_by("-validity_start")
        )
        return qs.annotate(
            description=Subquery(current_descriptions.values("description")[:1]),
        )

    def with_current_descriptions(qs):
        """Returns a GeographicalArea queryset annotated with the result of a a
        GeographicalAreaDescription subquery's description values chained
        together, linking these two queries on version_group field."""
        current_descriptions = (
            GeographicalAreaDescription.objects.latest_approved()
            .filter(described_geographicalarea__version_group=OuterRef("version_group"))
            .order_by()
            .values("described_geographicalarea__version_group")
        )
        agg_descriptions = current_descriptions.annotate(
            chained_description=StringAgg("description", delimiter=" "),
        ).values("chained_description")
        return qs.annotate(
            description=Subquery(agg_descriptions[:1]),
        )


class GeographicalArea(TrackedModel, ValidityMixin, DescribedMixin):
    """
    A Geographical Area covers three distinct types of object:

        1) A Country
        2) A Region (a trading area which is not recognised as a country)
        3) A Grouping of the above

    These objects are generally used when linked to data structures such as measures.
    As a measure does not care to distinguish between a country, region or group,
    the 3 types are stored as one for relational purposes.

    As a country or region can belong to a group there is a self-referential many-to-many
    field which is restricted. Yet groups can also have parent groups - in which case
    measures must of the parent must also apply to a child. To accomodate this there is a
    separate foreign key for group to group relations.
    """

    record_code = "250"
    subrecord_code = "00"

    identifying_fields = ("sid",)

    url_pattern_name_prefix = "geo_area"

    sid = SignedIntSID(db_index=True)
    area_id = models.CharField(max_length=4, validators=[area_id_validator])
    area_code = models.PositiveSmallIntegerField(choices=AreaCode.choices)

    # This deals with countries and regions belonging to area groups
    memberships = models.ManyToManyField("self", through="GeographicalMembership")

    # This deals with subgroups of other groups
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)

    objects = PolymorphicManager.from_queryset(GeographicalAreaQuerySet)()

    indirect_business_rules = (
        business_rules.GA14,
        business_rules.GA16,
        business_rules.GA17,
        measures_business_rules.ME1,
        measures_business_rules.ME65,
        measures_business_rules.ME66,
        measures_business_rules.ME67,
        quotas_business_rules.ON13,
        quotas_business_rules.ON14,
        quotas_business_rules.ON6,
    )
    business_rules = (
        business_rules.GA1,
        business_rules.GA3,
        business_rules.GA4,
        business_rules.GA5,
        business_rules.GA6,
        business_rules.GA7,
        business_rules.GA10,
        business_rules.GA11,
        business_rules.GA21,
        business_rules.GA22,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    def get_current_memberships(self):
        return (
            GeographicalMembership.objects.filter(
                Q(geo_group__sid=self.sid) | Q(member__sid=self.sid),
            )
            .current()
            .select_related("member", "geo_group")
        )

    def is_single_region_or_country(self):
        return self.area_code == AreaCode.COUNTRY or self.area_code == AreaCode.REGION

    def is_all_countries(self):
        return self.area_code == AreaCode.GROUP and self.area_id == "1011"

    def is_group(self):
        return self.area_code == AreaCode.GROUP

    def __str__(self):
        return f"{self.get_area_code_display()} {self.area_id}"

    class Meta:
        constraints = (
            CheckConstraint(
                name="only_groups_have_parents",
                check=Q(area_code=1) | Q(parent__isnull=True),
            ),
        )


class GeographicalMembership(GetTabURLMixin, TrackedModel, ValidityMixin):
    """
    A Geographical Membership describes the membership of a region or country to
    a group.

    Only a region or a country may be a member, and only a group can be a group.

    The validity ranges of all memberships must also fit completely within the
    validity ranges of the groups.
    """

    url_pattern_name_prefix = "geo_area"
    url_suffix = "#memberships"
    url_relation_field = "geo_group"

    record_code = "250"
    subrecord_code = "15"

    geo_group = models.ForeignKey(
        GeographicalArea,
        related_name="members",
        on_delete=models.PROTECT,
    )
    member = models.ForeignKey(
        GeographicalArea,
        related_name="groups",
        on_delete=models.PROTECT,
    )

    identifying_fields = ("geo_group__sid", "member__sid")

    business_rules = (
        business_rules.GA12,
        business_rules.GA13,
        business_rules.GA16,
        business_rules.GA17,
        business_rules.GA18,
        business_rules.GA20,
        business_rules.GA23,
        UpdateValidity,
    )

    def __str__(self):
        return (
            f"{self.geo_group.get_area_code_display()} "
            f"{self.geo_group.structure_description} member "
            f"{self.member.get_area_code_display()} "
            f"{self.member.structure_description}"
        )

    def other(self, area: GeographicalArea) -> GeographicalArea:
        """
        When passed an area that is part of this membership, returns the other
        area in the membership.

        So if the geo group is passed this returns the member, and if the member
        is passed this returns the geo group. Raises a ValueError if an object
        is passed that is neither of these.
        """
        if area.sid == self.geo_group.sid:
            return self.member
        elif area.sid == self.member.sid:
            return self.geo_group
        else:
            raise ValueError(f"{area} is not part of membership {self}")

    def member_used_in_measure_exclusion(self, transaction):
        return self.member.in_use(transaction, "measureexcludedgeographicalarea")


class GeographicalAreaDescription(DescriptionMixin, TrackedModel):
    record_code = "250"
    subrecord_code = "10"

    period_record_code = "250"
    period_subrecord_code = "05"

    identifying_fields = ("sid",)

    described_geographicalarea = models.ForeignKey(
        GeographicalArea,
        on_delete=models.CASCADE,
        related_name="descriptions",
        db_index=True,
    )
    description = ShortDescription()
    sid = SignedIntSID(db_index=True)

    def save(self, *args, **kwargs):
        if getattr(self, "sid") is None:
            highest_sid = GeographicalAreaDescription.objects.aggregate(Max("sid"))[
                "sid__max"
            ]
            self.sid = highest_sid + 1

        return super().save(*args, **kwargs)

    url_pattern_name_prefix = "geo_area_description"

    class Meta:
        ordering = ("validity_start",)
