from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.db import models
from django.db.models import CheckConstraint
from django.db.models import F
from django.db.models import Q

from common.models import ShortDescription
from common.models import SignedIntSID
from common.models import TrackedModel
from common.models import ValidityMixin
from geo_areas import validators


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

    sid = SignedIntSID()
    area_id = models.CharField(max_length=4, validators=[validators.area_id_validator])
    area_code = models.PositiveSmallIntegerField(choices=validators.AreaCode.choices)

    # This deals with countries and regions belonging to area groups
    memberships = models.ManyToManyField("self", through="GeographicalMembership")

    # This deals with subgroups of other groups
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)

    def get_description(self):
        return self.geographicalareadescription_set.last()

    def validate_workbasket(self):
        validators.validate_at_least_one_description(self)

    def __str__(self):
        return f'"{self.get_area_code_display()}" SID:{self.sid}'

    class Meta:
        constraints = (
            # GA1 and GA7
            ExclusionConstraint(
                name="exclude_overlapping_areas",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("area_id", RangeOperators.EQUAL),
                ],
            ),
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
        GeographicalArea, related_name="members", on_delete=models.PROTECT
    )
    member = models.ForeignKey(
        GeographicalArea, related_name="groups", on_delete=models.PROTECT
    )

    identifying_fields = ("geo_group", "member")

    def clean(self):
        validators.validate_group_is_group(self)
        validators.validate_member_is_country_or_region(self)
        validators.validate_group_validity_includes_membership_validity(self)
        validators.validate_members_of_child_group_are_in_parent_group(self)

    def __str__(self):
        return f"<{self.member}> -> <{self.geo_group}>"

    class Meta:
        constraints = (
            # GA18
            ExclusionConstraint(
                name="exclude_overlapping_memberships",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    (F("geo_group"), RangeOperators.EQUAL),
                    (F("member"), RangeOperators.EQUAL),
                ],
            ),
        )


class GeographicalAreaDescription(TrackedModel, ValidityMixin):
    record_code = "250"
    subrecord_code = "10"

    period_record_code = "250"
    period_subrecord_code = "05"

    area = models.ForeignKey(GeographicalArea, on_delete=models.CASCADE)
    description = ShortDescription()
    sid = SignedIntSID()

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="exclude_overlapping_area_descriptions",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("area", RangeOperators.EQUAL),
                ],
            ),
        ]

    def clean(self):
        validators.validate_description_is_not_null(self)
        validators.validate_geographical_area_description_have_unique_start_date(self)
        validators.validate_geographical_area_description_start_date_before_geographical_area_end_date(
            self
        )
        validators.validate_first_geographical_area_description_has_geographical_area_start_date(
            self
        )

    def __str__(self):
        return f'description ({self.sid}) - "{self.description}" for {self.area}'
