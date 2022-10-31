"""Business rules for measures."""
from datetime import date
from typing import Mapping
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.db.utils import DataError

from common.business_rules import BusinessRule
from common.business_rules import ExclusionMembership
from common.business_rules import FootnoteApplicability
from common.business_rules import MustExist
from common.business_rules import MustExistNotNull
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained
from common.business_rules import only_applicable_after
from common.business_rules import skip_when_deleted
from common.models.utils import override_current_transaction
from common.util import TaricDateRange
from common.util import validity_range_contains_range
from common.validators import ApplicabilityCode
from geo_areas.validators import AreaCode
from measures.querysets import MeasuresQuerySet
from quotas.models import QuotaOrderNumberOrigin
from quotas.validators import AdministrationMechanism

# 140 - MEASURE TYPE SERIES


class MTS1(UniqueIdentifyingFields):
    """The measure type series must be unique."""


class MTS2(PreventDeleteIfInUse):
    """The measure type series cannot be deleted if it is associated with a
    measure type."""


# 235 - MEASURE TYPE


class MT1(UniqueIdentifyingFields):
    """The measure type code must be unique."""


class MT3(ValidityPeriodContained):
    """When a measure type is used in a measure then the validity period of the
    measure type must span the validity period of the measure."""

    contained_field_name = "measure"


class MT4(MustExist):
    """The referenced measure type series must exist."""

    reference_field_name = "measure_type_series"


class MT7(PreventDeleteIfInUse):
    """A measure type cannot be deleted if it is in use in a measure."""

    via_relation = "measure"


class MT10(ValidityPeriodContained):
    """The validity period of the measure type series must span the validity
    period of the measure type."""

    container_field_name = "measure_type_series"


# 350 - MEASURE CONDITION CODE


class MC1(UniqueIdentifyingFields):
    """The code of the measure condition code must be unique."""


class MC3(ValidityPeriodContained):
    """If a measure condition code is used in a measure then the validity period
    of the measure condition code must span the validity period of the
    measure."""

    container_field_name = "condition_code"
    contained_field_name = "dependent_measure"


class MC4(PreventDeleteIfInUse):
    """The measure condition code cannot be deleted if it is used in a measure
    condition component."""


# 355 - MEASURE ACTION


class MA1(UniqueIdentifyingFields):
    """The code of the measure action must be unique."""


class MA2(PreventDeleteIfInUse):
    """The measure action cannot be deleted if it is used in a measure condition
    component."""


class MA4(ValidityPeriodContained):
    """If a measure action is used in a measure then the validity period of the
    measure action must span the validity period of the measure."""

    container_field_name = "action"
    contained_field_name = "dependent_measure"


# 430 - MEASURE


class ME1(UniqueIdentifyingFields):
    """The combination of measure type, geographical area, goods nomenclature
    item id, additional code type, additional code, order number, reduction
    indicator and start date must be unique."""

    identifying_fields = (
        "measure_type",
        "geographical_area",
        "goods_nomenclature",
        "additional_code",
        "dead_additional_code",
        "order_number",
        "dead_order_number",
        "reduction",
        "valid_between__lower",
    )


class ME2(MustExist):
    """The measure type must exist."""

    reference_field_name = "measure_type"


class ME3(ValidityPeriodContained):
    """The validity period of the measure type must span the validity period of
    the measure."""

    container_field_name = "measure_type"


class ME4(MustExist):
    """The geographical area must exist."""

    reference_field_name = "geographical_area"


class ME5(ValidityPeriodContained):
    """The validity period of the geographical area must span the validity
    period of the measure."""

    container_field_name = "geographical_area"


class ME6(MustExistNotNull):
    """The goods code must exist."""

    reference_field_name = "goods_nomenclature"


class ME7(BusinessRule):
    """
    The goods nomenclature code must be a product code.

    It may not be an intermediate line.
    """

    def validate(self, measure):
        # Simply calling measure.goods_nomenclature may not work
        # when the good is updated with a new suffix
        # (it will only work if the measure itself is changing)
        # due to the fact that the measure's good foreign key
        # will now point to the old version of the good
        # and this test will be futile.
        good = (
            type(measure.goods_nomenclature)
            .objects.filter(
                sid=measure.goods_nomenclature.sid,
                valid_between__overlap=measure.effective_valid_between,
            )
            .order_by(
                "-transaction__partition",
                "transaction__order",
            )
            .last()
        )
        if good and good.suffix != "80":
            raise self.violation(measure)


class ME8(ValidityPeriodContained):
    """The validity period of the goods code must span the validity period of
    the measure."""

    container_field_name = "goods_nomenclature"


class ME88(BusinessRule):
    """The level of the goods code cannot exceed the explosion level of the
    measure type."""

    def validate(self, measure):
        if not measure.goods_nomenclature:
            return

        goods = (
            type(measure.goods_nomenclature)
            .objects.filter(
                sid=measure.goods_nomenclature.sid,
                valid_between__overlap=measure.effective_valid_between,
            )
            .approved_up_to_transaction(measure.transaction)
        )

        explosion_level = measure.measure_type.measure_explosion_level

        if any(
            not good.item_id.endswith("0" * (10 - explosion_level)) for good in goods
        ):
            raise self.violation(measure)


@only_applicable_after("2004-12-31")
class ME16(BusinessRule):
    """Integrating a measure with an additional code when an equivalent or
    overlapping measures without additional code already exists and vice-versa,
    should be forbidden."""

    def validate(self, measure):
        kwargs = {}
        if measure.order_number:
            kwargs["order_number__order_number"] = measure.order_number.order_number
        elif measure.dead_order_number:
            kwargs["dead_order_number"] = measure.dead_order_number
        else:
            kwargs["order_number__isnull"] = True
            kwargs["dead_order_number__isnull"] = True

        if measure.additional_code or measure.dead_additional_code:
            additional_code_query = Q(additional_code__isnull=True) & Q(
                dead_additional_code__isnull=True,
            )
        else:
            additional_code_query = Q(additional_code__isnull=False) | Q(
                dead_additional_code__isnull=False,
            )
        if (
            type(measure)
            .objects.with_effective_valid_between()
            .filter(
                additional_code_query,
                measure_type__sid=measure.measure_type.sid,
                geographical_area__sid=measure.geographical_area.sid,
                goods_nomenclature__sid=measure.goods_nomenclature.sid
                if measure.goods_nomenclature
                else None,
                reduction=measure.reduction,
                db_effective_valid_between__overlap=measure.effective_valid_between,
                **kwargs,
            )
            .exclude(pk=measure.pk or None)
            .excluding_versions_of(version_group=measure.version_group)
            .approved_up_to_transaction(measure.transaction)
            .exists()
        ):
            raise self.violation(
                measure,
                "A measure with an additional code cannot be added when an equivalent "
                "or overlapping measure without an additional code already exists and "
                "vice-versa.",
            )


class ME115(ValidityPeriodContained):
    """The validity period of the referenced additional code must span the
    validity period of the measure."""

    container_field_name = "additional_code"


class ME25(BusinessRule):
    """If the measure’s end date is specified (implicitly or explicitly) then
    the start date of the measure must be less than or equal to the end date."""

    def validate(self, measure):
        try:
            effective_end_date = measure.effective_end_date

            if effective_end_date is None:
                return

            if measure.valid_between.lower > effective_end_date:
                raise self.violation(measure)
        except DataError:
            # ``effective_end_date`` will raise a database error if it tries to
            # compute the date and it breaks this rule
            raise self.violation(measure)


@skip_when_deleted
class ME32(BusinessRule):
    """
    There may be no overlap in time with other measure occurrences with a goods
    code in the same nomenclature hierarchy which references the same measure
    type, geo area, order number, additional code and reduction indicator.

    This rule is not applicable for Meursing additional codes.
    """

    def compile_query(self, measure):
        query = Q(
            measure_type__sid=measure.measure_type.sid,
            geographical_area__sid=measure.geographical_area.sid,
            reduction=measure.reduction,
        )
        if measure.order_number is not None:
            query &= Q(order_number__sid=measure.order_number.sid)
        elif measure.dead_order_number is not None:
            query &= Q(dead_order_number=measure.dead_order_number)
        else:
            query &= Q(order_number__isnull=True, dead_order_number__isnull=True)

        if measure.additional_code is not None:
            query &= Q(additional_code__sid=measure.additional_code.sid)
        elif measure.dead_additional_code is not None:
            query &= Q(dead_additional_code=measure.dead_additional_code)
        else:
            query &= Q(additional_code__isnull=True, dead_additional_code__isnull=True)

        return query

    def clashing_measures(self, measure) -> MeasuresQuerySet:
        """
        Returns all of the measures that clash with the passed measure over its
        lifetime.

        Two measures clash if any of their fields listed in this business rule
        description are equal, their date ranges overlap, and one of their
        commodity codes is an ancestor or equal to the other.
        """
        from measures.snapshots import MeasureSnapshot

        query = self.compile_query(measure)
        clashing_measures = type(measure).objects.none()
        for snapshot in MeasureSnapshot.get_snapshots(measure, self.transaction):
            clashing_measures = clashing_measures.union(
                snapshot.overlaps(measure).filter(query),
                all=True,
            )

        return clashing_measures

    def validate(self, measure):
        if measure.goods_nomenclature is None:
            return

        if self.clashing_measures(measure).exists():
            raise self.violation(measure)


# -- Ceiling/quota definition existence


class ME10(BusinessRule):
    """
    The order number must be specified if the "order number flag" (specified in
    the measure type record) has the value "mandatory".

    If the flag is set to "not permitted" then the field cannot be entered.
    """

    def validate(self, measure):
        if measure.order_number and measure.measure_type.order_number_not_permitted:
            raise self.violation(
                measure,
                'If the order number flag is set to "not permitted" then the order number '
                "cannot be entered.",
            )

        if (
            not measure.order_number
            and not measure.dead_order_number
            and measure.measure_type.order_number_mandatory
        ):
            raise self.violation(
                measure,
                'The order number must be specified if the "order number flag" has the '
                'value "mandatory".',
            )


@only_applicable_after("2007-12-31")
class ME116(ValidityPeriodContained):
    """When a quota order number is used in a measure then the validity period
    of the quota order number must span the validity period of the measure."""

    container_field_name = "order_number"


@only_applicable_after("2007-12-31")
class ME117(BusinessRule):
    """
    When a measure has a quota measure type then the origin must exist as a
    quota order number origin.

    Only origins for quota order numbers managed by the first come first served
    principle are in scope; these order number are starting with '09'; except order
    numbers starting with '094'.

    Quota measure types are the following:
        122 - Non preferential tariff quota
        123 - Non preferential tariff quota under end-use
        143 - Preferential tariff quota
        146 - Preferential tariff quota under end-use
        147 - Customs Union Quota
    """

    def validate(self, measure):
        from quotas.models import QuotaOrderNumberOrigin

        if measure.order_number is None:
            return

        if measure.order_number.mechanism != AdministrationMechanism.FCFS:
            return

        # check the measure geo area exists as a quota order number origin (and is not
        # excluded)
        origin = QuotaOrderNumberOrigin.objects.filter(
            Q(geographical_area__sid=measure.geographical_area.sid)
            | Q(geographical_area__members__member__sid=measure.geographical_area.sid),
            order_number__sid=measure.order_number.sid,
        )

        excluded_origins = QuotaOrderNumberOrigin.objects.filter(
            excluded_areas__sid=measure.geographical_area.sid,
            order_number__sid=measure.order_number.sid,
        )
        if origin.exists() and not excluded_origins.exists():
            return

        raise self.violation(measure)


@only_applicable_after("2007-12-31")
class ME119(ValidityPeriodContained):
    """When a quota order number is used in a measure then the validity period
    of the quota order number origin must span the validity period of the
    measure."""

    # This checks the same thing as ON10 from the other side of the relation

    def validate(self, measure):
        """
        Get all current QuotaOrderNumberOrigin objects associated with a
        measure's QuotaOrderNumber.

        Loop over these and raise a violation if the measure validity period is
        not contained by any of the origins
        """
        if not measure.order_number:
            return

        with override_current_transaction(self.transaction):
            contained_measure = measure.get_versions().current().get()

            origins = QuotaOrderNumberOrigin.objects.current().filter(
                order_number__order_number=measure.order_number.order_number,
            )

            for origin in origins:
                valid_between = origin.valid_between
                if validity_range_contains_range(
                    valid_between,
                    contained_measure.valid_between,
                ):
                    return

            raise self.violation(measure)


class QuotaOriginMatchingArea(BusinessRule):
    """When a quota order number is used in a measure then the quota order
    number origin's geographical area(s) must match those of the measure."""

    def validate(self, measure):
        # Return if the measure has no order number and, therefore, no order number origin
        if not measure.order_number:
            return

        # Get all individual countries / regions associated with the measure
        with override_current_transaction(self.transaction):
            if measure.geographical_area.area_code == AreaCode.GROUP:
                area_sids = set(
                    [
                        m.member.sid
                        for m in measure.geographical_area.memberships.current()
                    ],
                )
            else:
                area_sids = set([measure.geographical_area.sid])

            # Get all individual countries / regions for each quota order number origin linked to the measure
            origins = QuotaOrderNumberOrigin.objects.current().filter(
                order_number__order_number=measure.order_number.order_number,
            )
            origin_sids = []
            for origin in origins:
                if origin.geographical_area.area_code == AreaCode.GROUP:
                    for a in [
                        m.member for m in origin.geographical_area.memberships.current()
                    ]:
                        origin_sids.append(a.sid)
                else:
                    origin_sids.append(origin.geographical_area.sid)

            origin_sids = set(origin_sids)

            # Check that the geographical area sid is included in the list of origin area sids
            if any(area_sids - origin_sids):
                raise self.violation(measure)


# -- Relation with additional codes


class ME9(BusinessRule):
    """
    If no additional code is specified then the goods code is mandatory.

    A measure can be assigned to:

    - a commodity code only (most measures)
    - a commodity code plus an additional code (e.g. trade remedies, pharma duties,
      routes of ingress)
    - an additional code only (only for Meursing codes, which will be removed in the UK
      tariff).

    This means that a goods code is always mandatory in the UK tariff, however this
    business rule is still needed for historical EU measures.
    """

    def validate(self, measure):
        if measure.additional_code or measure.dead_additional_code:
            return

        if not measure.goods_nomenclature:
            raise self.violation(measure)


class ME12(BusinessRule):
    """If the additional code is specified then the additional code type must
    have a relationship with the measure type."""

    def validate(self, measure):
        AdditionalCodeTypeMeasureType = (
            measure.measure_type.additional_code_types.through
        )
        if (
            measure.additional_code
            and not AdditionalCodeTypeMeasureType.objects.approved_up_to_transaction(
                self.transaction,
            )
            .filter(
                additional_code_type__sid=measure.additional_code.type.sid,
                measure_type__sid=measure.measure_type.sid,
            )
            .exists()
        ):
            raise self.violation(measure)


class ME17(MustExist):
    """
    If the additional code type has as application "non-Meursing" then the
    additional code must exist as a non-Meursing additional code.

    UK tariff does not use meursing tables, so this is essentially saying that an
    additional code must exist.

    This refers to the fact that the TARIC Measure record has separate
    additional_code_type and additional_code fields. Our data model combines these into
    a single foreign key relation to AdditionalCode.

    It is not possible to violate this rule as a result.
    """

    reference_field_name = "additional_code"


# -- Export Refund nomenclature measures

# -- Export Refund for Processed Agricultural Goods measures

# -- Relation with regulations


class ME24(MustExist):
    """
    The role + regulation id must exist.

    If no measure start date is specified it defaults to the regulation start
    date.
    """

    reference_field_name = "generating_regulation"


class ME27(BusinessRule):
    """The entered regulation may not be fully replaced."""

    # Here we assume "fully replaced" means that there exists a Replacement that
    # covers the full validity period of the generating regulation.
    #
    # This method only checks that a single Replacement does this whereas it
    # might be possible for multiple Replacements to cover the full validity
    # period. However, the very few Regulations that have >1 Replacement have
    # been manually checked and don't require this extra complexity, and we
    # don't use Replacements in the UK so it won't be possible to create them.

    def validate(self, measure):
        with override_current_transaction(self.transaction):
            measures = type(measure).objects.filter(pk=measure.pk)
            regulation_validity = measures.follow_path("generating_regulation").get()
            replacements = measures.follow_path(
                "generating_regulation__replacements__enacting_regulation",
            ).filter(valid_between__contains=regulation_validity.valid_between)

            if replacements.exists():
                raise self.violation(measure)


class ME87(BusinessRule):
    """
    The validity period of the measure (implicit or explicit) must reside within
    the effective validity period of its supporting regulation.

    The effective validity period is the validity period of the regulation taking into
    account extensions and abrogation.

    A regulation’s validity period is hugely complex in the EU’s world.

    - A regulation is initially assigned a start date. It may be assigned an end date as
      well at the point of creation but this is rare.
    - The EU then may choose to end date the regulation using its end date field – in
      this case provision must be made to end date all of the measures that would
      otherwise extend beyond the end of this regulation end date.
    - The EU may also choose to end date the measure (regulation?) via 2 other means which we are
      abandoning (abrogation and prorogation).
    - Only the measure validity end date and the regulation validity end date field will
      need to be compared in the UK Tariff. However, in terminating measures from the EU
      tariff to make way for UK equivalents, and to avoid data clashes such as ME32, we DO
      need to be aware of this multiplicity of end dates.
    """

    def validate(self, measure):
        if (
            not measure.effective_valid_between.upper_inf
            and measure.effective_valid_between.upper < date(2008, 1, 1)
        ):
            # Exclude measure ending before 2008 - ME87 only counts from 2008 onwards.
            return

        regulation_validity = measure.generating_regulation.valid_between
        effective_end_date = measure.generating_regulation.effective_end_date

        if effective_end_date:
            regulation_validity = TaricDateRange(
                regulation_validity.lower,
                date(
                    year=effective_end_date.year,
                    month=effective_end_date.month,
                    day=effective_end_date.day,
                ),
            )

        if not validity_range_contains_range(
            regulation_validity,
            measure.effective_valid_between,
        ):
            raise self.violation(measure)


class ME33(BusinessRule):
    """A justification regulation may not be entered if the measure end date is
    not filled in."""

    def validate(self, measure):
        if (
            measure.valid_between.upper is None
            and measure.terminating_regulation is not None
        ):
            raise self.violation(measure)


class ME34(BusinessRule):
    """A justification regulation must be entered if the measure end date is
    filled in."""

    def validate(self, measure):
        if (
            measure.valid_between.upper is not None
            and measure.terminating_regulation is None
        ):
            raise self.violation(measure)


# -- Measure component


class ME40(BusinessRule):
    """
    If the flag "duty expression" on measure type is "mandatory" then at least
    one measure component or measure condition component record must be
    specified.  If the flag is set "not permitted" then no measure component or
    measure condition component must exist.  Measure components and measure
    condition components are mutually exclusive. A measure can have either
    components or condition components (if the "duty expression" flag is
    "mandatory" or "optional") but not both.

    This describes the fact that measures of certain types MUST have components
    (duties) assigned to them, whereas others must not. Note the sub-clause also
    – if the value of the field “Component applicable” is set to 1 (mandatory)
    on a measure type, then when the measure is created, there must be either
    measure components or measure condition components assigned to the measure,
    but not both. CDS will generate errors if either of these conditions are not
    met.
    """

    def validate(self, measure):
        has_components = measure.has_components(self.transaction)
        has_condition_components = measure.has_condition_components(self.transaction)

        if measure.measure_type.components_mandatory and not (
            has_components or has_condition_components
        ):
            raise self.violation(
                measure,
                'If the flag "duty expression" on measure type is "mandatory" then '
                "at least one measure component or measure condition component "
                "record must be specified.",
            )

        elif measure.measure_type.components_not_permitted and (
            has_components or has_condition_components
        ):
            raise self.violation(
                measure,
                'If the flag "duty expression" on measure type is "not permitted" then no '
                "measure component or measure condition must exist.",
            )

        if has_components and has_condition_components:
            raise self.violation(
                measure,
                "Measure components and measure condition components are mutually "
                "exclusive.",
            )


class ME41(MustExist):
    """The referenced duty expression must exist."""

    reference_field_name = "duty_expression"


class ME42(ValidityPeriodContained):
    """The validity period of the duty expression must span the validity period
    of the measure."""

    container_field_name = "duty_expression"
    contained_field_name = "component_measure"


class ME43(BusinessRule):
    """
    The same duty expression can only be used once with the same measure.

    Even if an expression that (in English) reads the same needs to be used more
    than once in a measure, we must use a different expression ID, never the
    same one twice.
    """

    def validate(self, measure_component):
        duty_expressions_used = (
            type(measure_component)
            .objects.approved_up_to_transaction(measure_component.transaction)
            .exclude(pk=measure_component.pk if measure_component.pk else None)
            .excluding_versions_of(version_group=measure_component.version_group)
            .filter(
                component_measure__sid=measure_component.component_measure.sid,
            )
            .values_list("duty_expression__sid", flat=True)
        )

        if measure_component.duty_expression.sid in duty_expressions_used:
            raise self.violation(measure_component)


class ComponentApplicability(BusinessRule):
    """Rule enforcing component applicability."""

    messages: Mapping[int, str] = {
        ApplicabilityCode.MANDATORY: 'If the flag "{0.component_name}" on duty expression '
        'is "mandatory" then {0.article} {0.component_name} must be specified.',
        ApplicabilityCode.NOT_PERMITTED: 'If the flag "{0.component_name}" on duty '
        'expression is "not permitted" then no {0.component_name} may be entered.',
    }
    applicability_field: Optional[str] = None
    article: str = "a"
    component_name: str
    component_field: str

    def get_components(self, measure):
        raise NotImplementedError()

    def get_applicability_field(self):
        return self.applicability_field or (
            f"duty_expression__{self.component_field}_applicability_code"
        )

    def validate(self, measure):
        components = self.get_components(measure)

        for code in (
            ApplicabilityCode.MANDATORY,
            ApplicabilityCode.NOT_PERMITTED,
        ):

            inapplicable = Q(**{self.get_applicability_field(): code}) & Q(
                **{
                    f"{self.component_field}__isnull": code
                    == ApplicabilityCode.MANDATORY,
                }
            )
            if (
                components.filter(inapplicable)
                .approved_up_to_transaction(self.transaction)
                .exists()
            ):
                raise self.violation(measure, self.messages[code].format(self))


class MeasureComponentApplicability(ComponentApplicability):
    def get_components(self, measure):
        return measure.components.select_related("duty_expression")


class ME45(MeasureComponentApplicability):
    """
    If the flag "amount" on duty expression is "mandatory" then an amount must
    be specified.

    If the flag is set "not permitted" then no amount may be entered.
    """

    article = "an"
    component_name = "amount"
    component_field = "duty_amount"


class ME46(MeasureComponentApplicability):
    """
    If the flag "monetary unit" on duty expression is "mandatory" then a
    monetary unit must be specified.

    If the flag is set "not permitted" then no monetary unit may be entered.
    """

    component_name = "monetary unit"
    component_field = "monetary_unit"


class ME47(MeasureComponentApplicability):
    """
    If the flag "measurement unit" on duty expression is "mandatory" then a
    measurement unit must be specified.

    If the flag is set "not permitted" then no measurement unit may be entered.
    """

    applicability_field = "duty_expression__measurement_unit_applicability_code"
    component_name = "measurement unit"
    component_field = "component_measurement__measurement_unit"


class ME48(MustExist):
    """The referenced monetary unit must exist."""

    reference_field_name = "monetary_unit"


class ME49(ValidityPeriodContained):
    """The validity period of the referenced monetary unit must span the
    validity period of the measure."""

    container_field_name = "monetary_unit"
    contained_field_name = "component_measure"


class ME50(MustExist):
    """The combination measurement unit + measurement unit qualifier must
    exist."""

    reference_field_name = "component_measurement"


class ME51(ValidityPeriodContained):
    """The validity period of the measurement unit must span the validity period
    of the measure."""

    container_field_name = "component_measurement__measurement_unit"
    contained_field_name = "component_measure"


class ME52(ValidityPeriodContained):
    """The validity period of the measurement unit qualifier must span the
    validity period of the measure."""

    container_field_name = "component_measurement__measurement_unit_qualifier"
    contained_field_name = "component_measure"


# -- Measure condition and Measure condition component


class ME53(MustExist):
    """The referenced measure condition must exist."""

    reference_field_name = "condition"


class ME56(MustExist):
    """The referenced certificate must exist."""

    reference_field_name = "required_certificate"


class ME57(ValidityPeriodContained):
    """The validity period of the referenced certificate must span the validity
    period of the measure."""

    container_field_name = "required_certificate"
    contained_field_name = "dependent_measure"


class ME58(BusinessRule):
    """The same certificate, volume or price can only be referenced once by the
    same measure and the same condition type."""

    @staticmethod
    def match_related_model(model, key):
        obj = getattr(model, key)
        if obj is None:
            return {key: None}
        else:
            return {f"{key}__version_group": obj.version_group}

    def validate(self, measure_condition):
        kwargs = {
            "condition_code__code": measure_condition.condition_code.code,
            "dependent_measure__sid": measure_condition.dependent_measure.sid,
            "duty_amount": measure_condition.duty_amount,
            **self.match_related_model(measure_condition, "required_certificate"),
            **self.match_related_model(measure_condition, "condition_measurement"),
            **self.match_related_model(measure_condition, "monetary_unit"),
        }

        if (
            type(measure_condition)
            .objects.excluding_versions_of(
                version_group=measure_condition.version_group,
            )
            .filter(**kwargs)
            .approved_up_to_transaction(self.transaction)
            .exists()
        ):
            raise self.violation(measure_condition)


class ME59(MustExist):
    """The referenced action code must exist."""

    reference_field_name = "action"


class ME60(MustExist):
    """The referenced monetary unit must exist."""

    reference_field_name = "monetary_unit"


class ME61(ValidityPeriodContained):
    """The validity period of the referenced monetary unit must span the
    validity period of the measure."""

    container_field_name = "monetary_unit"
    contained_field_name = "dependent_measure"


class ME62(MustExist):
    """The combination measurement unit + measurement unit qualifier must
    exist."""

    reference_field_name = "condition_measurement"


class ME63(ValidityPeriodContained):
    """The validity period of the measurement unit must span the validity period
    of the measure."""

    container_field_name = "condition_measurement__measurement_unit"
    contained_field_name = "dependent_measure"


class ME64(ValidityPeriodContained):
    """The validity period of the measurement unit qualifier must span the
    validity period of the measure."""

    container_field_name = "condition_measurement__measurement_unit_qualifier"
    contained_field_name = "dependent_measure"


class ME105(MustExist):
    """The referenced duty expression must exist."""

    reference_field_name = "duty_expression"


class ME106(ValidityPeriodContained):
    """The validity period of the duty expression must span the validity period
    of the measure."""

    container_field_name = "duty_expression"
    contained_field_name = "condition__dependent_measure"


class ME108(BusinessRule):
    """
    The same duty expression can only be used once within condition components
    of the same condition of the same measure.

    (i.e. it can be re-used in other conditions, no matter what condition type,
    of the same measure).
    """

    def validate(self, component):
        if (
            type(component)
            .objects.approved_up_to_transaction(component.transaction)
            .exclude(pk=component.pk or None)
            .excluding_versions_of(version_group=component.version_group)
            .filter(
                condition__sid=component.condition.sid,
                duty_expression__sid=component.duty_expression.sid,
            )
            .exists()
        ):
            raise self.violation(component)


class ConditionCodeAcceptance(BusinessRule):
    """
    If a condition has a certificate, then the condition's code must accept a
    certificate.

    If a condition has a duty amount, then the condition's code must accept a
    price.
    """

    def validate(self, condition):
        code = condition.condition_code

        if condition.required_certificate and condition.duty_amount:
            raise self.violation(
                message="Conditions may only be created with one of either certificate or price",
            )

        message = f"Condition with code {code.code} cannot accept "
        if condition.required_certificate and not code.accepts_certificate:
            raise self.violation(message=message + "a certificate")

        if condition.duty_amount and not code.accepts_price:
            raise self.violation(message=message + "a price")


class ActionRequiresDuty(BusinessRule):
    """If a condition's action code requires a duty, then an associated
    condition component must be created with a duty amount."""

    def validate(self, condition):
        components = condition.components.approved_up_to_transaction(self.transaction)
        components_have_duty = any([c.duty_amount is not None for c in components])
        if condition.action.requires_duty and not components_have_duty:
            raise self.violation(
                message=f"Condition with action code {condition.action.code} must have at least one component with a duty amount",
            )

        if not condition.action.requires_duty and components_have_duty:
            raise self.violation(
                message=f"Condition with action code {condition.action.code} should not have any components with a duty amount",
            )


class MeasureConditionComponentApplicability(ComponentApplicability):
    def get_components(self, measure):
        return measure.conditions.prefetch_related("components").select_related(
            "components__duty_expression",
        )


class ME109(MeasureConditionComponentApplicability):
    """
    If the flag 'amount' on duty expression is 'mandatory' then an amount must
    be specified.

    If the flag is set to 'not permitted' then no amount may be entered.
    """

    article = "an"
    component_name = "amount"
    component_field = "components__duty_amount"
    applicability_field = "components__duty_expression__duty_amount_applicability_code"


class ME110(MeasureConditionComponentApplicability):
    """
    If the flag 'monetary unit' on duty expression is 'mandatory' then a
    monetary unit must be specified.

    If the flag is set to 'not permitted' then no monetary unit may be entered.
    """

    component_name = "monetary unit"
    component_field = "components__monetary_unit"
    applicability_field = (
        "components__duty_expression__monetary_unit_applicability_code"
    )


class ME111(MeasureConditionComponentApplicability):
    """
    If the flag 'measurement unit' on duty expression is 'mandatory' then a
    measurement unit must be specified.

    If the flag is set to 'not permitted' then no measurement unit may be
    entered.
    """

    component_name = "measurement unit"
    component_field = "components__component_measurement__measurement_unit"
    applicability_field = (
        "components__duty_expression__measurement_unit_applicability_code"
    )


# -- Measure excluded geographical area


class ME65(BusinessRule):
    """An exclusion can only be entered if the measure is applicable to a geographical
    area group (area code = 1).
    """

    def validate(self, exclusion):
        if exclusion.modified_measure.geographical_area.area_code != AreaCode.GROUP:
            raise self.violation(exclusion)


class ME66(ExclusionMembership):
    """The excluded geographical area must be a member of the geographical area
    group."""

    excluded_from = "modified_measure"


class ME67(BusinessRule):
    """The membership period of the excluded geographical area must span the
    valid period of the measure."""

    def validate(self, exclusion):
        GeographicalMembership = type(
            exclusion.excluded_geographical_area,
        ).memberships.through

        geo_group = exclusion.modified_measure.geographical_area
        excluded = exclusion.excluded_geographical_area

        if (
            not GeographicalMembership.objects.approved_up_to_transaction(
                self.transaction,
            )
            .as_at(
                exclusion.modified_measure.effective_valid_between,
            )
            .filter(
                geo_group__version_group=geo_group.version_group,
                member__version_group=excluded.version_group,
            )
            .exists()
        ):
            raise self.violation(exclusion)


class ME68(BusinessRule):
    """The same geographical area can only be excluded once by the same
    measure."""

    def validate(self, exclusion):
        if (
            type(exclusion)
            .objects.filter(
                excluded_geographical_area__sid=exclusion.excluded_geographical_area.sid,
                modified_measure__sid=exclusion.modified_measure.sid,
            )
            .excluding_versions_of(version_group=exclusion.version_group)
            .exists()
        ):
            raise self.violation(exclusion)


# -- Footnote association


class ME69(MustExist):
    """The associated footnote must exist."""

    reference_field_name = "associated_footnote"


class ME70(BusinessRule):
    """The same footnote can only be associated once with the same measure."""

    def validate(self, association):
        if (
            type(association)
            .objects.approved_up_to_transaction(association.transaction)
            .exclude(pk=association.pk or None)
            .excluding_versions_of(version_group=association.version_group)
            .filter(
                footnoted_measure__sid=association.footnoted_measure.sid,
                associated_footnote__footnote_id=association.associated_footnote.footnote_id,
                associated_footnote__footnote_type__footnote_type_id=association.associated_footnote.footnote_type.footnote_type_id,
            )
            .exists()
        ):
            raise self.violation(association)


class ME71(FootnoteApplicability):
    """Footnotes with a footnote type for which the application type = "CN footnotes"
    cannot be associated with TARIC codes (codes with pos. 9-10 different from 00).
    """

    applicable_field = "footnoted_measure"


class ME73(ValidityPeriodContained):
    """The validity period of the associated footnote must span the validity
    period of the measure."""

    container_field_name = "associated_footnote"
    contained_field_name = "footnoted_measure"


# -- Partial temporary stop

# -- Justification regulation


class ME104(BusinessRule):
    """
    The justification regulation must be either:

        - the measure’s measure-generating regulation, or
        - a measure-generating regulation, valid on the day after the measure’s
          (explicit) end date.

    If the measure’s measure-generating regulation is ‘approved’, then so must be the
    justification regulation.
    """

    def validate(self, measure):
        generating = measure.generating_regulation
        terminating = measure.terminating_regulation

        if terminating is None:
            return

        # TODO: Verify this is needed
        # if generating.approved and not terminating.approved:
        #     raise self.violation(
        #         measure,
        #         "If the measure's measure-generating regulation is 'approved', then so "
        #         "must be the justification regulation.",
        #     )

        if (
            terminating.regulation_id == generating.regulation_id
            and terminating.role_type == generating.role_type
        ):
            return

        # TODO: verify this day (should be 2004-01-01 really, except for measure 2700491 (at least), and 2939413))
        # TODO: And carrying on past 2020 with 3784976
        if 1 or measure.valid_between.lower < date(2007, 7, 1):
            return

        valid_day = measure.effective_end_date + relativedelta(days=1)
        if valid_day not in terminating.valid_between:
            amends = terminating.amends.first()
            if amends and valid_day in TaricDateRange(
                amends.valid_between.lower,
                terminating.valid_between.upper,
            ):
                return

            raise self.violation(
                measure,
                "The justification regulation must be either the measure's measure-generating "
                "regulation, or a measure-generating regulation valid on the day after the "
                "measure's end date.",
            )
