from django.db import models

from common.fields import ShortDescription
from common.fields import SignedIntSID
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

    def in_use(self):
        # TODO handle deletes
        return self.measures.model.objects.filter(
            geographical_area__sid=self.sid,
        ).exists()

    def is_a_parent(self):
        # TODO handle deletes
        return GeographicalArea.objects.filter(
            parent__sid=self.sid,
        ).exists()

    def __str__(self):
        return f"{self.get_area_code_display()} {self.area_id}"


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

    identifying_fields = ("geo_group_id", "member_id")

    def member_used_in_measure_exclusion(self):
        # TODO handle deletes
        return self.member.measureexcludedgeographicalarea_set.model.objects.filter(
            excluded_geographical_area__sid=self.member.sid,
        ).exists()


class GeographicalAreaDescription(TrackedModel, ValidityMixin):
    record_code = "250"
    subrecord_code = "10"

    period_record_code = "250"
    period_subrecord_code = "05"

    area = models.ForeignKey(
        GeographicalArea, on_delete=models.CASCADE, related_name="descriptions"
    )
    description = ShortDescription()
    sid = SignedIntSID()
