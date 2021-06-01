from django.db import models
from django.db.models import CheckConstraint
from django.db.models import Max
from django.db.models import Q

from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import TrackedModel
from common.models.mixins.description import DescriptionMixin
from common.models.mixins.validity import ValidityMixin
from geo_areas import business_rules
from geo_areas import validators
from measures import business_rules as measures_business_rules
from quotas import business_rules as quotas_business_rules


class GeographicalArea(TrackedModel, ValidityMixin):
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

    url_pattern_name_prefix = "geoarea"

    sid = SignedIntSID(db_index=True)
    area_id = models.CharField(max_length=4, validators=[validators.area_id_validator])
    area_code = models.PositiveSmallIntegerField(choices=validators.AreaCode.choices)

    # This deals with countries and regions belonging to area groups
    memberships = models.ManyToManyField("self", through="GeographicalMembership")

    # This deals with subgroups of other groups
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)

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
    )

    def get_current_memberships(self):
        return (
            GeographicalMembership.objects.filter(
                Q(geo_group__sid=self.sid) | Q(member__sid=self.sid),
            )
            .latest_approved()
            .select_related("member", "geo_group")
        )

    def in_use(self):
        return (
            self.measures.model.objects.filter(
                geographical_area__sid=self.sid,
            )
            .approved_up_to_transaction(self.transaction)
            .exists()
        )

    def is_a_parent(self):
        return (
            GeographicalArea.objects.filter(
                parent__sid=self.sid,
            )
            .approved_up_to_transaction(self.transaction)
            .exists()
        )

    def __str__(self):
        return f"{self.get_area_code_display()} {self.area_id}"

    class Meta:
        constraints = (
            CheckConstraint(
                name="only_groups_have_parents",
                check=Q(area_code=1) | Q(parent__isnull=True),
            ),
        )


class GeographicalMembership(TrackedModel, ValidityMixin):
    """
    A Geographical Membership describes the membership of a region or country to
    a group.

    Only a region or a country may be a member, and only a group can be a group.

    The validity ranges of all memberships must also fit completely within the validity
    ranges of the groups.
    """

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
    )

    def other(self, area: GeographicalArea) -> GeographicalArea:
        """
        When passed an area that is part of this membership, returns the other
        area in the membership.

        So if the geo group is passed this returns the member, and if the member
        is passed this returns the geo group. Raises a ValueError if an object
        is passed that is neither of these.
        """
        if area == self.geo_group:
            return self.member
        elif area == self.member:
            return self.geo_group
        else:
            raise ValueError(f"{area} is not part of membership {self}")

    def member_used_in_measure_exclusion(self):
        return (
            self.member.measureexcludedgeographicalarea_set.model.objects.filter(
                excluded_geographical_area__sid=self.member.sid,
            )
            .approved_up_to_transaction(self.transaction)
            .exists()
        )


class GeographicalAreaDescription(DescriptionMixin, TrackedModel):
    record_code = "250"
    subrecord_code = "10"

    period_record_code = "250"
    period_subrecord_code = "05"

    described_geographicalarea = models.ForeignKey(
        GeographicalArea,
        on_delete=models.CASCADE,
        related_name="descriptions",
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

    class Meta:
        ordering = ("validity_start",)
