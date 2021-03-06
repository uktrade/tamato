"""Business rules for measures."""
from datetime import datetime
from datetime import timezone
from typing import Mapping
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.db.models import Q

from common.business_rules import BusinessRule
from common.business_rules import MustExist
from common.business_rules import only_applicable_after
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained
from common.util import TaricDateTimeRange
from common.util import validity_range_contains_range
from common.validators import ApplicabilityCode
from footnotes.validators import ApplicationCode
from geo_areas.validators import AreaCode
from quotas.validators import AdministrationMechanism


class MeasureValidityPeriodContained(ValidityPeriodContained):
    def query_contains_validity(self, container, contained, model):
        queryset = container.__class__.objects.filter(
            **container.get_identifying_fields(),
        ).current()

        if container.__class__.__name__ == "Measure":
            queryset = queryset.with_effective_valid_between().filter(
                db_effective_valid_between__contains=contained.valid_between
            )
        elif contained.__class__.__name__ == "Measure":
            queryset = queryset.filter(
                valid_between__contains=contained.effective_valid_between
            )
        else:
            queryset = queryset.filter(valid_between__contains=contained.valid_between)

        if not queryset.exists():
            raise self.violation(model)


# 140 - MEASURE TYPE SERIES


class MTS1(UniqueIdentifyingFields):
    """The measure type series must be unique."""


class MTS2(PreventDeleteIfInUse):
    """The measure type series cannot be deleted if it is associated with a measure type."""


# 235 - MEASURE TYPE


class MT1(UniqueIdentifyingFields):
    """The measure type code must be unique."""


class MT3(MeasureValidityPeriodContained):
    """When a measure type is used in a measure then the validity period of the measure
    type must span the validity period of the measure.
    """

    container_field_name = "measure_type"


class MT4(MustExist):
    """The referenced measure type series must exist."""

    reference_field_name = "measure_type_series"


class MT7(PreventDeleteIfInUse):
    """A measure type cannot be deleted if it is in use in a measure."""


class MT10(ValidityPeriodContained):
    """The validity period of the measure type series must span the validity period of
    the measure type.
    """

    container_field_name = "measure_type_series"


# 350 - MEASURE CONDITION CODE


class MC1(UniqueIdentifyingFields):
    """The code of the measure condition code must be unique."""


class MC3(MeasureValidityPeriodContained):
    """If a measure condition code is used in a measure then the validity period of the
    measure condition code must span the validity period of the measure.
    """

    container_field_name = "condition_code"
    contained_field_name = "dependent_measure"


class MC4(PreventDeleteIfInUse):
    """The measure condition code cannot be deleted if it is used in a measure condition
    component.
    """

    in_use_check = "used_in_component"


# 355 - MEASURE ACTION


class MA1(UniqueIdentifyingFields):
    """The code of the measure action must be unique."""


class MA2(PreventDeleteIfInUse):
    """The measure action cannot be deleted if it is used in a measure condition component."""


class MA4(MeasureValidityPeriodContained):
    """If a measure action is used in a measure then the validity period of the measure
    action must span the validity period of the measure.
    """

    container_field_name = "action"
    contained_field_name = "dependent_measure"


# 430 - MEASURE


class ME1(UniqueIdentifyingFields):
    """The combination of measure type + geographical area + goods nomenclature item id
    + additional code type + additional code + order number + reduction indicator +
    start date must be unique.
    """

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


class ME3(MeasureValidityPeriodContained):
    """The validity period of the measure type must span the validity period of the measure."""

    container_field_name = "measure_type"


class ME4(MustExist):
    """The geographical area must exist."""

    reference_field_name = "geographical_area"


class ME5(MeasureValidityPeriodContained):
    """The validity period of the geographical area must span the validity period of the measure."""

    container_field_name = "geographical_area"


class ME6(MustExist):
    """The goods code must exist."""

    reference_field_name = "goods_nomenclature"


class ME7(BusinessRule):
    """The goods nomenclature code must be a product code. It may not be an intermediate line.

    test"""

    def validate(self, measure):
        if measure.goods_nomenclature and measure.goods_nomenclature.suffix != "80":
            raise self.violation(measure)


class ME8(MeasureValidityPeriodContained):
    """The validity period of the goods code must span the validity period of the measure."""

    container_field_name = "goods_nomenclature"


class ME88(BusinessRule):
    """The level of the goods code cannot exceed the explosion level of the measure type."""

    def validate(self, measure):
        if not measure.goods_nomenclature:
            return

        goods = (
            type(measure.goods_nomenclature)
            .objects.filter(
                sid=measure.goods_nomenclature.sid,
                valid_between__overlap=measure.effective_valid_between,
            )
            .current()
        )

        explosion_level = measure.measure_type.measure_explosion_level

        if any(
            not good.item_id.endswith("0" * (10 - explosion_level)) for good in goods
        ):
            raise self.violation(measure)


@only_applicable_after("2004-12-31")
class ME16(BusinessRule):
    """Integrating a measure with an additional code when an equivalent or overlapping
    measures without additional code already exists and vice-versa, should be
    forbidden.
    """

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
                dead_additional_code__isnull=True
            )
        else:
            additional_code_query = Q(additional_code__isnull=False) | Q(
                dead_additional_code__isnull=False
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
            .exclude(pk=measure.pk if measure.pk else None)
            .excluding_versions_of(version_group=measure.version_group)
            .current()
            .exists()
        ):
            raise self.violation(
                measure,
                "A measure with an additional code cannot be added when an equivalent "
                "or overlapping measure without an additional code already exists and "
                "vice-versa.",
            )


class ME115(MeasureValidityPeriodContained):
    """The validity period of the referenced additional code must span the validity
    period of the measure.
    """

    container_field_name = "additional_code"


class ME25(BusinessRule):
    """If the measure’s end date is specified (implicitly or explicitly) then the start
    date of the measure must be less than or equal to the end date.
    """

    def validate(self, measure):
        if measure.valid_between.lower > measure.effective_end_date:
            raise self.violation(measure)


class ME32(BusinessRule):
    """There may be no overlap in time with other measure occurrences with a goods code
    in the same nomenclature hierarchy which references the same measure type, geo area,
    order number, additional code and reduction indicator.

    This rule is not applicable for Meursing additional codes.
    """

    def validate(self, measure):
        if measure.goods_nomenclature is None:
            return

        # build the query for measures matching the given measure
        query = Q(
            measure_type__sid=measure.measure_type.sid,
            geographical_area__sid=measure.geographical_area.sid,
        )
        if measure.order_number is not None:
            query &= Q(order_number__sid=measure.order_number.sid)
        if measure.additional_code is not None:
            query &= Q(additional_code__sid=measure.additional_code.sid)
        if measure.reduction is not None:
            query &= Q(reduction=measure.reduction)
        matching_measures = type(measure).objects.filter(query).current()

        # get all goods nomenclature versions associated with this measure
        GoodsNomenclature = type(measure.goods_nomenclature)
        goods = GoodsNomenclature.objects.filter(
            sid=measure.goods_nomenclature.sid,
            valid_between__overlap=measure.effective_valid_between,
        )

        # hack to avoid circular import
        Node = GoodsNomenclature.indents.rel.related_model.nodes.rel.related_model

        # for each goods nomenclature version, get all indents
        for good in goods:
            indents = Node.objects.filter(
                valid_between__overlap=measure.effective_valid_between,
                indent__indented_goods_nomenclature=good,
            )

            # for each indent, get the goods tree
            for indent in indents:
                tree = (indent.get_ancestors() | indent.get_descendants()).filter(
                    valid_between__overlap=measure.effective_valid_between,
                )

                # check for any measures associated to commodity codes in the tree which
                # clash with the specified measure
                if matching_measures.filter(
                    goods_nomenclature__indents__nodes__in=tree.values_list(
                        "pk", flat=True
                    ),
                    valid_between__overlap=measure.effective_valid_between,
                ).exists():
                    raise self.violation(measure)


# -- Ceiling/quota definition existence


class ME10(BusinessRule):
    """The order number must be specified if the "order number flag" (specified in the
    measure type record) has the value "mandatory". If the flag is set to "not
    permitted" then the field cannot be entered.
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
class ME116(MeasureValidityPeriodContained):
    """When a quota order number is used in a measure then the validity period of the
    quota order number must span the validity period of the measure.
    """

    container_field_name = "order_number"


@only_applicable_after("2007-12-31")
class ME117(BusinessRule):
    """When a measure has a quota measure type then the origin must exist as a quota
    order number origin.

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
class ME119(BusinessRule):
    """When a quota order number is used in a measure then the validity period of the
    quota order number origin must span the validity period of the measure.
    """

    # This checks the same thing as ON10 from the other side of the relation

    def validate(self, measure):
        # TODO: Ignore this for now - the data from HMRC has violations. Investigate and fix later.
        return
        if not measure.order_number:
            return

        if (
            measure.order_number.quotaordernumberorigin_set.model.objects.filter(
                order_number__sid=measure.order_number.sid,
            )
            .exclude(
                valid_between__contains=measure.effective_valid_between,
            )
            .exists()
        ):
            raise self.violation(measure)


# -- Relation with additional codes


class ME9(BusinessRule):
    """If no additional code is specified then the goods code is mandatory.

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
    """If the additional code is specified then the additional code type must have a
    relationship with the measure type.
    """

    def validate(self, measure):
        if (
            measure.additional_code
            and not measure.measure_type.additional_code_types.filter(
                sid=measure.additional_code.type.sid
            ).exists()
        ):
            raise self.violation(measure)


class ME17(MustExist):
    """If the additional code type has as application "non-Meursing" then the additional
    code must exist as a non-Meursing additional code.

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
    """The role + regulation id must exist. If no measure start date is specified it
    defaults to the regulation start date.
    """

    reference_field_name = "generating_regulation"


class ME87(BusinessRule):
    """The validity period of the measure (implicit or explicit) must reside within the
    effective validity period of its supporting regulation.

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
            and measure.effective_valid_between.upper
            < datetime(2008, 1, 1, tzinfo=timezone.utc)
        ):
            # Exclude measure ending before 2008 - ME87 only counts from 2008 onwards.
            return

        regulation_validity = measure.generating_regulation.valid_between
        effective_end_date = measure.generating_regulation.effective_end_date

        if effective_end_date:
            regulation_validity = TaricDateTimeRange(
                regulation_validity.lower,
                datetime(
                    year=effective_end_date.year,
                    month=effective_end_date.month,
                    day=effective_end_date.day,
                    tzinfo=timezone.utc,
                ),
            )

        if not validity_range_contains_range(
            regulation_validity,
            measure.effective_valid_between,
        ):
            raise self.violation(measure)


class ME33(BusinessRule):
    """"A justification regulation may not be entered if the measure end date is not filled in."""

    def validate(self, measure):
        if (
            measure.effective_valid_between.upper is None
            and measure.terminating_regulation is not None
        ):
            raise self.violation(measure)


class ME34(BusinessRule):
    """A justification regulation must be entered if the measure end date is filled in."""

    def validate(self, measure):
        if (
            measure.valid_between.upper is not None
            and measure.terminating_regulation is None
        ):
            raise self.violation(measure)


# -- Measure component


class ME40(BusinessRule):
    """If the flag "duty expression" on measure type is "mandatory" then at least one
    measure component or measure condition component record must be specified.  If the
    flag is set "not permitted" then no measure component or measure condition component
    must exist.  Measure components and measure condition components are mutually
    exclusive. A measure can have either components or condition components
    (if the ‘duty expression’ flag is ‘mandatory’ or ‘optional’) but not both.

    This describes the fact that measures of certain types MUST have components (duties)
    assigned to them, whereas others must not. Note the sub-clause also – if the value
    of the field “Component applicable” is set to 1 (mandatory) on a measure type, then
    when the measure is created, there must be either measure components or measure
    condition components assigned to the measure, but not both. CDS will generate errors
    if either of these conditions are not met.
    """

    def validate(self, measure):
        has_components = measure.has_components()
        has_condition_components = measure.has_condition_components()

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


class ME42(MeasureValidityPeriodContained):
    """The validity period of the duty expression must span the validity period of the measure."""

    container_field_name = "duty_expression"
    contained_field_name = "component_measure"


class ME43(BusinessRule):
    """The same duty expression can only be used once with the same measure.

    Even if an expression that (in English) reads the same needs to be used more than
    once in a measure, we must use a different expression ID, never the same one twice.
    """

    def validate(self, measure_component):
        duty_expressions_used = (
            type(measure_component)
            .objects.approved()
            .with_workbasket(measure_component.transaction.workbasket)
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
            if components.filter(inapplicable).current().exists():
                raise self.violation(measure, self.messages[code].format(self))


class MeasureComponentApplicability(ComponentApplicability):
    def get_components(self, measure):
        return measure.components.select_related("duty_expression")


class ME45(MeasureComponentApplicability):
    """If the flag "amount" on duty expression is "mandatory" then an amount must be
    specified. If the flag is set "not permitted" then no amount may be entered.
    """

    article = "an"
    component_name = "amount"
    component_field = "duty_amount"


class ME46(MeasureComponentApplicability):
    """If the flag "monetary unit" on duty expression is "mandatory" then a monetary
    unit must be specified. If the flag is set "not permitted" then no monetary unit may
    be entered.
    """

    component_name = "monetary unit"
    component_field = "monetary_unit"


class ME47(MeasureComponentApplicability):
    """If the flag "measurement unit" on duty expression is "mandatory" then a
    measurement unit must be specified. If the flag is set "not permitted" then no
    measurement unit may be entered.
    """

    applicability_field = "duty_expression__measurement_unit_applicability_code"
    component_name = "measurement unit"
    component_field = "component_measurement__measurement_unit"


class ME48(MustExist):
    """The referenced monetary unit must exist."""

    reference_field_name = "monetary_unit"


class ME49(MeasureValidityPeriodContained):
    """The validity period of the referenced monetary unit must span the validity period
    of the measure."""

    container_field_name = "monetary_unit"
    contained_field_name = "component_measure"


class ME50(MustExist):
    """The combination measurement unit + measurement unit qualifier must exist."""

    reference_field_name = "component_measurement"


class ME51(MeasureValidityPeriodContained):
    """The validity period of the measurement unit must span the validity period of the
    measure."""

    container_field_name = "component_measurement__measurement_unit"
    contained_field_name = "component_measure"


class ME52(MeasureValidityPeriodContained):
    """The validity period of the measurement unit qualifier must span the validity
    period of the measure.
    """

    container_field_name = "component_measurement__measurement_unit_qualifier"
    contained_field_name = "component_measure"


# -- Measure condition and Measure condition component


class ME53(MustExist):
    """The referenced measure condition must exist."""

    reference_field_name = "condition"


class ME56(MustExist):
    """The referenced certificate must exist."""

    reference_field_name = "required_certificate"


class ME57(MeasureValidityPeriodContained):
    """The validity period of the referenced certificate must span the validity period
    of the measure.
    """

    container_field_name = "required_certificate"
    contained_field_name = "dependent_measure"


class ME58(BusinessRule):
    """The same certificate can only be referenced once by the same measure and the same
    condition type.
    """

    def validate(self, measure_condition):
        if measure_condition.required_certificate is None:
            return

        if (
            type(measure_condition)
            .objects.approved()
            .with_workbasket(measure_condition.transaction.workbasket)
            .exclude(pk=measure_condition.pk if measure_condition.pk else None)
            .excluding_versions_of(version_group=measure_condition.version_group)
            .filter(
                condition_code__code=measure_condition.condition_code.code,
                required_certificate__sid=measure_condition.required_certificate.sid,
                required_certificate__certificate_type__sid=measure_condition.required_certificate.certificate_type.sid,
                dependent_measure__sid=measure_condition.dependent_measure.sid,
            )
            .current()
            .exists()
        ):
            raise self.violation(measure_condition)


class ME59(MustExist):
    """The referenced action code must exist."""

    reference_field_name = "action"


class ME60(MustExist):
    """The referenced monetary unit must exist."""

    reference_field_name = "monetary_unit"


class ME61(MeasureValidityPeriodContained):
    """The validity period of the referenced monetary unit must span the validity period
    of the measure.
    """

    container_field_name = "monetary_unit"
    contained_field_name = "dependent_measure"


class ME62(MustExist):
    """The combination measurement unit + measurement unit qualifier must exist."""

    reference_field_name = "condition_measurement"


class ME63(MeasureValidityPeriodContained):
    """The validity period of the measurement unit must span the validity period of the measure."""

    container_field_name = "condition_measurement__measurement_unit"
    contained_field_name = "dependent_measure"


class ME64(MeasureValidityPeriodContained):
    """The validity period of the measurement unit qualifier must span the validity
    period of the measure.
    """

    container_field_name = "condition_measurement__measurement_unit_qualifier"
    contained_field_name = "dependent_measure"


class ME105(MustExist):
    """The referenced duty expression must exist."""

    reference_field_name = "duty_expression"


class ME106(MeasureValidityPeriodContained):
    """The validity period of the duty expression must span the validity period of the measure."""

    container_field_name = "duty_expression"
    contained_field_name = "condition__dependent_measure"


class ME108(BusinessRule):
    """The same duty expression can only be used once within condition components of the
    same condition of the same measure.

    (i.e. it can be re-used in other conditions, no matter what condition type, of the
    same measure).
    """

    def validate(self, component):
        if (
            type(component)
            .objects.approved()
            .with_workbasket(component.transaction.workbasket)
            .exclude(pk=component.pk if component.pk else None)
            .excluding_versions_of(version_group=component.version_group)
            .filter(
                condition__sid=component.condition.sid,
                duty_expression__sid=component.duty_expression.sid,
            )
            .exists()
        ):
            raise self.violation(component)


class MeasureConditionComponentApplicability(ComponentApplicability):
    def get_components(self, measure):
        return measure.conditions.prefetch_related("components").select_related(
            "components__duty_expression"
        )


class ME109(MeasureConditionComponentApplicability):
    """If the flag 'amount' on duty expression is 'mandatory' then an amount must be
    specified. If the flag is set to 'not permitted' then no amount may be entered.
    """

    article = "an"
    component_name = "amount"
    component_field = "components__duty_amount"
    applicability_field = "components__duty_expression__duty_amount_applicability_code"


class ME110(MeasureConditionComponentApplicability):
    """If the flag 'monetary unit' on duty expression is 'mandatory' then a monetary
    unit must be specified. If the flag is set to 'not permitted' then no monetary unit
    may be entered.
    """

    component_name = "monetary unit"
    component_field = "components__monetary_unit"
    applicability_field = (
        "components__duty_expression__monetary_unit_applicability_code"
    )


class ME111(MeasureConditionComponentApplicability):
    """If the flag 'measurement unit' on duty expression is 'mandatory' then a
    measurement unit must be specified. If the flag is set to 'not permitted' then no
    measurement unit may be entered.
    """

    component_name = "measurement unit"
    component_field = "components__condition_component_measurement__measurement_unit"
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


class ME66(BusinessRule):
    """The excluded geographical area must be a member of the geographical area group."""

    def validate(self, exclusion):
        geo_group = exclusion.modified_measure.geographical_area

        if not geo_group.memberships.filter(
            sid=exclusion.excluded_geographical_area.sid
        ).exists():
            raise self.violation(exclusion)


class ME67(BusinessRule):
    """The membership period of the excluded geographical area must span the valid
    period of the measure.
    """

    def validate(self, exclusion):
        return  # TODO: Verify this rule

        geo_group = exclusion.modified_measure.geographical_area
        excluded = exclusion.excluded_geographical_area

        if not geo_group.members.filter(
            member__sid=excluded.sid,
            valid_between__contains=exclusion.modified_measure.effective_valid_between,
        ).exists():
            raise self.violation(measure)


class ME68(BusinessRule):
    """The same geographical area can only be excluded once by the same measure."""

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
            .objects.approved()
            .with_workbasket(association.transaction.workbasket)
            .exclude(pk=association.pk if association.pk else None)
            .excluding_versions_of(version_group=association.version_group)
            .filter(
                footnoted_measure__sid=association.footnoted_measure.sid,
                associated_footnote__footnote_id=association.associated_footnote.footnote_id,
                associated_footnote__footnote_type__footnote_type_id=association.associated_footnote.footnote_type.footnote_type_id,
            )
            .exists()
        ):
            raise self.violation(association)


class ME71(BusinessRule):
    """Footnotes with a footnote type for which the application type = "CN footnotes"
    cannot be associated with TARIC codes (codes with pos. 9-10 different from 00).
    """

    def validate(self, association):
        measure = association.footnoted_measure
        if measure.goods_nomenclature is None:
            return

        commodity_code = measure.goods_nomenclature.item_id

        is_taric_code = len(commodity_code) <= 8 or commodity_code[8:] != "00"
        application_code = (
            association.associated_footnote.footnote_type.application_code
        )

        if is_taric_code and application_code == ApplicationCode.CN_MEASURES:
            raise self.violation(measure)


class ME73(MeasureValidityPeriodContained):
    """The validity period of the associated footnote must span the validity period of
    the measure."""

    container_field_name = "associated_footnote"
    contained_field_name = "footnoted_measure"


# -- Partial temporary stop

# -- Justification regulation


class ME104(BusinessRule):
    """The justification regulation must be either:

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
        if 1 or measure.valid_between.lower < datetime(2007, 7, 1, tzinfo=timezone.utc):
            return

        valid_day = measure.effective_end_date + relativedelta(days=1)
        if valid_day not in terminating.valid_between:
            amends = terminating.amends.first()
            if amends and valid_day in TaricDateTimeRange(
                amends.valid_between.lower, terminating.valid_between.upper
            ):
                return

            raise self.violation(
                measure,
                "The justification regulation must be either the measure's measure-generating "
                "regulation, or a measure-generating regulation valid on the day after the "
                "measure's end date.",
            )
