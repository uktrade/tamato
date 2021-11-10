"""Business rules for geographical areas."""
from django.db import connection
from django.db.models import F

from common.business_rules import BusinessRule
from common.business_rules import DescriptionsRules
from common.business_rules import MustExist
from common.business_rules import NoOverlapping
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContains
from common.business_rules import only_applicable_after
from geo_areas.validators import AreaCode


class GA1(UniqueIdentifyingFields):
    """The combination geographical area id + validity start date must be
    unique."""

    identifying_fields = ("area_id", "valid_between__lower")


@only_applicable_after("1998-02-01")
class DescriptionNotEmpty(BusinessRule):
    """A description cannot be blank."""

    def validate(self, description):
        if not description.description:
            raise self.violation(description)


class GA3(DescriptionsRules):
    """
    At least one description record is mandatory.

    The start date of the first description period must be equal to the start
    date of the geographical area. Two descriptions may not have the same start
    date. The start date of the description must be less than or equal to the
    end date of the geographical area.
    """

    model_name = "geographical area"


class GA4(BusinessRule):
    """The referenced parent geographical area group must be an existing geographical
    area with area code = 1 (geographical area group).
    """

    def validate(self, geo_area):
        try:
            if geo_area.parent is None:
                return
        except geo_area.ObjectDoesNotExist:
            raise self.violation(geo_area)

        if geo_area.parent.area_code != AreaCode.GROUP:
            raise self.violation(geo_area)


class GA5(BusinessRule):
    """If a geographical area has a parent geographical area group then the
    validity period of the parent geographical area group must span the validity
    period of the geographical area."""

    def validate(self, geo_area):
        if (
            type(geo_area)
            .objects.select_related("parent")
            .filter(
                parent__isnull=False,
                sid=geo_area.sid,
            )
            .approved_up_to_transaction(self.transaction)
            .exclude(
                parent__valid_between__contains=F("valid_between"),
            )
            .exists()
        ):
            raise self.violation(geo_area)


class GA6(BusinessRule):
    """
    Loops in the parent relation between geographical areas and parent
    geographical area groups are not allowed.

    If a geographical area A is a parent geographical area group of B then B
    cannot be a parent geographical area group of A (loops can also exist on
    more than two levels, e.g. level 3; If A is a parent of B and B is a parent
    of C then C cannot be a parent of A).
    """

    def validate(self, geo_group):
        # Use a recursive CTE to detect loops
        max_depth = 20  # how deep does the geographical area tree go?
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE hierarchy AS (
                    SELECT parent_id AS ancestor_id, trackedmodel_ptr_id AS descendant_id, 1 AS depth
                    FROM geo_areas_geographicalarea
                    UNION ALL
                    SELECT hierarchy.ancestor_id, ga.trackedmodel_ptr_id, hierarchy.depth + 1 AS depth
                    FROM hierarchy
                    JOIN geo_areas_geographicalarea ga
                        ON hierarchy.descendant_id = ga.parent_id
                    WHERE hierarchy.depth < %s
                )
                SELECT DISTINCT ancestor_id
                FROM hierarchy
                WHERE ancestor_id = descendant_id AND descendant_id=%s
                """,
                [max_depth, geo_group.id],
            )
            row = cursor.fetchone()

        if row:
            raise self.violation(geo_group)


class GA7(NoOverlapping):
    """The validity period of geographical area must not overlap any other
    geographical area with the same geographical area id."""

    identifying_fields = ("area_id",)


class GA10(ValidityPeriodContains):
    """When a geographical area is referenced in a measure then the validity
    period of the geographical area must span the validity period of the
    measure."""

    contained_field_name = "measures"


class GA11(BusinessRule):
    """If a geographical area is referenced as an excluded geographical area in
    a measure then the membership period of the geographical area must span the
    validity period of the measure."""

    def validate(self, geo_area):
        Measure = (
            geo_area.measureexcludedgeographicalarea_set.model.modified_measure.field.related_model
        )
        if (
            Measure.objects.with_effective_valid_between()
            .approved_up_to_transaction(geo_area.transaction)
            .filter(exclusions__excluded_geographical_area__sid=geo_area.sid)
            .exclude(db_effective_valid_between__contained_by=geo_area.valid_between)
            .exists()
        ):
            raise self.violation(geo_area)


class GA12(MustExist):
    """The referenced geographical area id (member) must exist."""

    reference_field_name = "member"


class GA13(BusinessRule):
    """Group member must be a Country or Region, not a Group."""

    def validate(self, membership):
        if membership.member.area_code == AreaCode.GROUP:
            raise self.violation(membership)


class GA14(MustExist):
    """The referenced geographical area group id must exist."""

    reference_field_name = "geo_group"


class GA16(BusinessRule):
    """The validity period of the geographical area group must span all
    membership periods of its members."""

    def validate(self, membership):
        if (
            type(membership)
            .objects.filter(
                geo_group=membership.geo_group,
            )
            .approved_up_to_transaction(membership.transaction)
            .exclude(
                valid_between__contained_by=membership.geo_group.valid_between,
            )
            .exists()
        ):
            raise self.violation(membership)


class GA17(BusinessRule):
    """The membership period of a geographical area (member) must be within
    (inclusive) the validity period of the geographical area group (geographical
    area’s start and end date)."""

    def validate(self, membership):
        if (
            type(membership)
            .objects.filter(
                geo_group=membership.geo_group,
            )
            .approved_up_to_transaction(membership.transaction)
            .exclude(
                valid_between__contained_by=membership.geo_group.valid_between,
            )
            .exists()
        ):
            raise self.violation(membership)


class GA18(BusinessRule):
    """When a geographical area is more than once member of the same group then
    there may be no overlap in their membership periods."""

    def validate(self, membership):
        if (
            type(membership)
            .objects.filter(
                geo_group=membership.geo_group,
                member=membership.member,
                valid_between__overlap=membership.valid_between,
            )
            .approved_up_to_transaction(membership.transaction)
            .exclude(
                id=membership.id,
            )
            .exists()
        ):
            raise self.violation(membership)


class GA19(BusinessRule):
    """If the associated geographical area group has a parent geographical area
    group then all the members of the geographical area group must also be
    members of the parent geographical area group."""

    def validate(self, membership):
        parent = membership.geo_group.parent

        if parent and not membership.member.groups.filter(geo_group=parent).exists():
            raise self.violation(membership)


class GA20(BusinessRule):
    """If the associated geographical area group has a parent geographical area
    group then the membership period of each member of the parent group must
    span the membership period of the same geographical area in the geographical
    area group."""

    def validate(self, membership):
        if not membership.geo_group.parent:
            return

        parent = membership.geo_group.parent.current_version

        if (
            parent.members.filter(
                member__sid=membership.member.sid,
            )
            .approved_up_to_transaction(membership.transaction)
            .exclude(
                valid_between__contains=membership.valid_between,
            )
            .exists()
        ):
            raise self.violation(membership)


class GA21(PreventDeleteIfInUse):
    """
    If a geographical area is referenced in a measure then it may not be
    deleted.

    The geographical area may be referenced in a measure as the
    origin/destination or as an excluded geographical area.
    """

    via_relation = "measures"


class GA22(PreventDeleteIfInUse):
    """A geographical area cannot be deleted if it is referenced as a parent
    geographical area group."""

    via_relation = "geographicalarea"


class GA23(PreventDeleteIfInUse):
    """If a geographical area is referenced as an excluded geographical area in
    a measure, the membership association with the measure geographical area
    group cannot be deleted."""

    in_use_check = "member_used_in_measure_exclusion"
