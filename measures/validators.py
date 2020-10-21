from datetime import datetime
from datetime import timedelta
from datetime import timezone

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

from commodities.models import GoodsNomenclatureIndentNode
from common.util import validity_range_contains_range
from common.validators import ApplicabilityCode
from common.validators import NumberRangeValidator
from footnotes.validators import ApplicationCode
from geo_areas.validators import AreaCode
from quotas.validators import AdministrationMechanism


measure_type_series_id_validator = RegexValidator(r"^[A-Z][A-Z ]?$")
measurement_unit_code_validator = RegexValidator(r"^[A-Z]{3}$")
measurement_unit_qualifier_code_validator = RegexValidator(r"^[A-Z]$")
monetary_unit_code_validator = RegexValidator(r"^[A-Z]{3}$")
measure_type_id_validator = RegexValidator(r"^[0-9]{3}|[0-9]{6}|[A-Z]{3}$")
measure_condition_code_validator = RegexValidator(r"^[A-Z][A-Z ]?$")


# XXX even though we can't add to or modify these, shouldn't they live in the DB?
class DutyExpressionId(models.TextChoices):
    """Duty expression IDs control how the duty amount is interpreted. Multiple duty
    expressions are concatenated in ID order, which is why multiple IDs have the same
    meaning.

    The following values (and their descriptions) are the only possible values
    without having a major impact on HMRC systems.
    """

    DE1 = "1", "% or amount"
    DE2 = "2", "minus % or amount"
    DE3 = "3", "The rate is replaced by the levy"
    DE4 = "4", "+ % or amount"
    DE5 = "5", "The rate is replaced by the reduced levy"
    DE6 = "6", "+ Suplementary amount"
    DE7 = "7", "+ Levy"
    DE9 = "9", "+ Reduced levy"
    DE11 = "11", "+ Variable component"
    DE12 = "12", "+ agricultural component"
    DE13 = "13", "+ Reduced variable component"
    DE14 = "14", "+ reduced agricultural component"
    DE15 = "15", "Minimum"
    DE17 = "17", "Maximum"
    DE19 = "19", "+ % or amount"
    DE20 = "20", "+ % or amount"
    DE21 = "21", "+ additional duty on sugar"
    DE23 = "23", "+ 2 % Additional duty on sugar"
    DE25 = "25", "+ reduced additional duty on sugar"
    DE27 = "27", "+ additional duty on flour"
    DE29 = "29", "+ reduced additional duty on flour"
    DE31 = "31", "Accession compensatory amount"
    DE33 = "33", "+ Accession compensatory amount"
    DE35 = "35", "Maximum"
    DE36 = "36", "minus % CIF"
    DE37 = "37", "(nothing)"
    DE40 = "40", "Export refunds for cereals"
    DE41 = "41", "Export refunds for rice"
    DE42 = "42", "Export refunds for eggs"
    DE43 = "43", "Export refunds for sugar"
    DE44 = "44", "Export refunds for milk products"
    DE99 = "99", "Supplementary unit"


class MeasureTypeCombination(models.IntegerChoices):
    SINGLE_MEASURE = 0, "Only 1 measure at export and 1 at import from the series"
    ALL_MEASURES = 1, "All measure types in the series to be considered"


class ImportExportCode(models.IntegerChoices):
    IMPORT = 0, "Import"
    EXPORT = 1, "Export"
    BOTH = 2, "Import/Export"


validate_priority_code = NumberRangeValidator(1, 9)


class OrderNumberCaptureCode(models.IntegerChoices):
    MANDATORY = 1, "Mandatory"
    NOT_PERMITTED = 2, "Not permitted"


def validate_measure_explosion_level(value):
    explosion_levels = [2, 4, 6, 8, 10]
    if value not in explosion_levels:
        raise ValidationError(f"Explosion level must be one of {explosion_levels}")


def validate_action_code(value):
    try:
        index = int(value)
    except ValueError as e:
        raise ValidationError(f"Action code must be a number")

    NumberRangeValidator(1, 999)(index)


validate_reduction_indicator = NumberRangeValidator(1, 3)

validate_component_sequence_number = NumberRangeValidator(1, 999)


def must_exist(obj, field_name, message=None):
    """Check that a foreign key links to an existing object unless nullable."""
    # TODO does an object need to exist in the database AND be
    # approved/published/active?

    if message is None:
        message = f"{obj.__class__.__name__} {field_name} must exist."

    try:
        if getattr(obj, field_name) is None:
            return
    except ObjectDoesNotExist as e:
        raise ValidationError({field_name: message}) from e


def validate_unique_measure_type_series(measure_type_series):
    """MTS1"""

    measure_type_series_with_overlapping_validity = (
        type(measure_type_series)
        .objects.approved()
        .filter(
            sid=measure_type_series.sid,
            valid_between__overlap=measure_type_series.valid_between,
        )
    )
    if measure_type_series_with_overlapping_validity.exists():
        raise ValidationError("The measure type series must be unique.")


def validate_unique_measure_type(measure_type):
    """MT1"""

    measure_type_with_overlapping_validity = (
        type(measure_type)
        .objects.approved()
        .filter(
            sid=measure_type.sid,
            valid_between__overlap=measure_type.valid_between,
        )
    )
    if measure_type_with_overlapping_validity.exists():
        raise ValidationError("The measure type code must be unique.")


def validate_measure_type_validity_spans_measure_validity(measure):
    """MT3"""

    if not validity_range_contains_range(
        measure.measure_type.valid_between, measure.valid_between
    ):
        raise ValidationError(
            "The validity period of the measure type must span the validity "
            "period of the measure."
        )


def validate_measure_type_series_validity_spans_measure_type_validity(measure_type):
    """MT10"""

    if not validity_range_contains_range(
        measure_type.measure_type_series.valid_between, measure_type.valid_between
    ):
        raise ValidationError(
            "The validity period of the measure type series must span the validity "
            "period of the measure type."
        )


def validate_unique_measure_condition_code(measure_condition_code):
    """MC1"""

    measure_condition_code_with_overlapping_validity = (
        type(measure_condition_code)
        .objects.approved()
        .filter(
            code=measure_condition_code.code,
            valid_between__overlap=measure_condition_code.valid_between,
        )
    )
    if measure_condition_code_with_overlapping_validity.exists():
        raise ValidationError("The code of the measure condition code must be unique.")


def validate_measure_condition_code_validity_spans_measure_validity(measure_condition):
    """MC3"""

    if not validity_range_contains_range(
        measure_condition.condition_code.valid_between,
        measure_condition.dependent_measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the measure condition code must span the validity "
            "period of the measure."
        )


def validate_unique_measure_action_code(measure_action):
    """MA1"""

    measure_action_with_overlapping_validity = (
        type(measure_action)
        .objects.approved()
        .filter(
            code=measure_action.code,
            valid_between__overlap=measure_action.valid_between,
        )
    )
    if measure_action_with_overlapping_validity.exists():
        raise ValidationError("The code of the measure action must be unique.")


def validate_measure_action_validity_spans_measure_validity(measure_condition):
    """MA4"""

    if measure_condition.action is None:
        return

    if not validity_range_contains_range(
        measure_condition.action.valid_between,
        measure_condition.dependent_measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the measure action must span the validity "
            "period of the measure."
        )


def validate_unique_measure(measure):
    """ME1"""

    measure_with_overlapping_validity = (
        type(measure)
        .objects.approved()
        .filter(
            measure_type=measure.measure_type,
            geographical_area=measure.geographical_area,
            goods_nomenclature=measure.goods_nomenclature,
            additional_code=measure.additional_code,
            order_number=measure.order_number,
            reduction=measure.reduction,
            valid_between__startswith=measure.valid_between.lower,
        )
    )
    if measure_with_overlapping_validity.exists():
        raise ValidationError(
            "The combination of measure type + geographical area + goods nomenclature "
            "item id + additional code type + additional code + order number + "
            "reduction indicator + start date must be unique."
        )


def validate_geo_area_validity_spans_measure_validity(measure):
    """ME5"""

    if not validity_range_contains_range(
        measure.geographical_area.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the geographical area must span the validity "
            "period of the measure."
        )


def validate_goods_nomenclature_is_a_product_code(measure):
    """ME7"""

    if measure.goods_nomenclature and measure.goods_nomenclature.suffix != "80":
        raise ValidationError(
            "The goods nomenclature code must be a product code. It may not be an "
            "intermediate line"
        )


def validate_goods_nomenclature_validity_spans_measure_validity(measure):
    """ME8"""

    if measure.goods_nomenclature and not validity_range_contains_range(
        measure.goods_nomenclature.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the goods code must span the validity "
            "period of the measure."
        )


def validate_goods_code_present_if_no_additional_code(measure):
    """ME9"""

    if measure.additional_code:
        return

    if not measure.goods_nomenclature:
        raise ValidationError(
            "If no additional code is specified then the goods code is mandatory"
        )


def validate_order_number_capture(measure):
    """ME10"""

    if measure.order_number and measure.measure_type.order_number_not_permitted:
        raise ValidationError(
            'If the order number flag is set to "not permitted" then the order number '
            "cannot be entered."
        )

    if not measure.order_number and measure.measure_type.order_number_mandatory:
        raise ValidationError(
            'The order number must be specified if the "order number flag" has the '
            'value "mandatory".'
        )


def validate_additional_code_associated_with_measure_type(measure):
    """ME12"""

    if (
        measure.additional_code
        and not measure.measure_type.additional_code_types.filter(
            sid=measure.additional_code.type.sid
        ).exists()
    ):
        raise ValidationError(
            "The additional code type must have a relationship with the measure type"
        )


def validate_measure_unique_except_additional_code(measure):
    """ME16"""

    query = {
        field: getattr(measure, field)
        for field in measure.identifying_fields
        if field != "additional_code"
    }
    if (
        type(measure)
        .objects.filter(**query)
        .exclude(pk=measure.pk if measure.pk else None)
        .exists()
    ):
        raise ValidationError(
            {
                "additional_code": "A measure with an additional code cannot be added "
                "when an equivalent or overlapping measure without an additional code "
                "already exists and vice-versa."
            }
        )


def validate_no_overlapping_measures_in_same_goods_hierarchy(measure):
    """ME32"""

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
    matching_measures = type(measure).objects.filter(query)

    # get all goods nomenclature versions associated with this measure
    goods = type(measure.goods_nomenclature).objects.filter(
        sid=measure.goods_nomenclature.sid,
        valid_between__overlap=measure.valid_between,
    )

    # for each goods nomenclature version, get all indents
    for good in goods:
        indents = GoodsNomenclatureIndentNode.objects.filter(
            valid_between__overlap=measure.valid_between,
            indent__indented_goods_nomenclature=good,
        )

        # for each indent, get the goods tree
        for indent in indents:
            tree = (indent.get_ancestors() | indent.get_descendants()).filter(
                valid_between__overlap=measure.valid_between,
            )

            # check for any measures associated to commodity codes in the tree which
            # clash with the specified measure
            if matching_measures.filter(
                goods_nomenclature__indents__nodes__in=tree.values_list("pk", flat=True)
            ).exists():
                raise ValidationError(
                    "There may be no overlap in time with other measure occurrences "
                    "with a goods code in the same nomenclature hierarchy which "
                    "references the same measure type, geographical area, order "
                    "number, additional code and reduction indicator."
                )


def validate_no_terminating_regulation_if_no_end_date(measure):
    """ME33"""

    if (
        measure.valid_between.upper is None
        and measure.terminating_regulation is not None
    ):
        raise ValidationError(
            "A justification regulation may not be entered if the measure end date is "
            "not filled in."
        )


def validate_terminating_regulation_if_end_date(measure):
    """ME34"""

    if (
        measure.valid_between.upper is not None
        and measure.terminating_regulation is None
    ):
        raise ValidationError(
            "A justification regulation must be entered if the measure end date is "
            "filled in."
        )


def validate_measure_has_required_components(measure):
    """ME40"""

    has_components = measure.has_components()
    has_condition_components = measure.has_condition_components()

    if measure.measure_type.components_mandatory and not (
        has_components or has_condition_components
    ):
        raise ValidationError(
            'If the flag "duty expression" on measure type is "mandatory" then '
            "at least one measure component or measure condition component "
            "record must be specified."
        )

    elif measure.measure_type.components_not_permitted and (
        has_components or has_condition_components
    ):
        raise ValidationError(
            'If the flag "duty expression" on measure type is "not permitted" then no '
            "measure component or measure condition must exist."
        )

    if has_components and has_condition_components:
        raise ValidationError(
            "Measure components and measure condition components are mutually "
            "exclusive."
        )


def validate_duty_expression_validity_spans_measure_validity(duty_expression, measure):
    """ME42 + ME106"""

    if not validity_range_contains_range(
        duty_expression.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the duty expression must span the validity "
            "period of the measure."
        )


def validate_measure_component_duty_expression_only_used_once_per_measure(
    measure_component,
):
    """ME43"""

    duty_expressions_used = (
        type(measure_component)
        .objects.approved()
        .with_workbasket(measure_component.workbasket)
        .exclude(pk=measure_component.pk if measure_component.pk else None)
        .filter(
            component_measure__sid=measure_component.component_measure.sid,
        )
        .values_list("duty_expression__sid", flat=True)
    )

    if measure_component.duty_expression.sid in duty_expressions_used:
        raise ValidationError(
            "The same duty expression can only be used once with the same measure."
        )


def validate_component_duty_amount(duty_expression, duty_amount):
    """ME45 + ME109"""

    use_of_amount = duty_expression.duty_amount_applicability_code

    if use_of_amount == ApplicabilityCode.MANDATORY and duty_amount is None:
        raise ValidationError(
            'If the flag "amount" on duty expression is "mandatory" then an amount '
            "must be specified."
        )

    if use_of_amount == ApplicabilityCode.NOT_PERMITTED and duty_amount is not None:
        raise ValidationError(
            'If the flag "amount" on duty expression is "not permitted" then no '
            "amount may be entered."
        )


def validate_component_monetary_unit(duty_expression, monetary_unit):
    """ME46 + ME110"""

    use_of_monetary_unit = duty_expression.monetary_unit_applicability_code

    if use_of_monetary_unit == ApplicabilityCode.MANDATORY and monetary_unit is None:
        raise ValidationError(
            'If the flag "monetary unit" on duty expression is "mandatory" then a '
            "monetary unit must be specified."
        )

    if (
        use_of_monetary_unit == ApplicabilityCode.NOT_PERMITTED
        and monetary_unit is not None
    ):
        raise ValidationError(
            'If the flag "monetary unit" on duty expression is "not permitted" then no '
            "monetary unit may be entered."
        )


def validate_component_measurement_unit(duty_expression, measurement):
    """ME47 + ME111"""

    use_of_measurement_unit = duty_expression.measurement_unit_applicability_code

    if use_of_measurement_unit == ApplicabilityCode.MANDATORY and measurement is None:
        raise ValidationError(
            'If the flag "measurement unit" on duty expression is "mandatory" then a '
            "measurement unit must be specified."
        )

    if (
        use_of_measurement_unit == ApplicabilityCode.NOT_PERMITTED
        and measurement is not None
    ):
        raise ValidationError(
            'If the flag "measurement unit" on duty expression is "not permitted" then no '
            "measurement unit may be entered."
        )


def validate_measure_component_monetary_unit_validity_spans_measure_validity(
    measure_component,
):
    """ME49"""

    if measure_component.monetary_unit is None:
        return

    if not validity_range_contains_range(
        measure_component.monetary_unit.valid_between,
        measure_component.component_measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the monetary unit must span the validity "
            "period of the measure."
        )


def validate_measurement_unit_validity_spans_measure_validity(measurement, measure):
    """ME51 + ME63"""

    if measurement is None:
        return

    if not validity_range_contains_range(
        measurement.measurement_unit.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the measurement unit must span the validity "
            "period of the measure."
        )


def validate_measurement_unit_qualifier_validity_spans_measure_validity(
    measurement, measure
):
    """ME52 + ME64"""

    if measurement is None:
        return

    if not validity_range_contains_range(
        measurement.measurement_unit_qualifier.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the measurement unit qualifier must span the validity "
            "period of the measure."
        )


def validate_condition_exists(measure_condition_component):
    try:
        if measure_condition_component.condition is None:
            return
    except ObjectDoesNotExist as e:
        raise ValidationError("The referenced measure condition must exist.") from e


def validate_measure_condition_certificate_validity_spans_measure_validity(
    measure_condition,
):
    """ME57"""

    if measure_condition.required_certificate is None:
        return

    if not validity_range_contains_range(
        measure_condition.required_certificate.valid_between,
        measure_condition.dependent_measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the referenced certificate must span the validity "
            "period of the measure."
        )


def validate_measure_condition_certificate_only_used_once_per_measure(
    measure_condition,
):
    """ME58"""

    if measure_condition.required_certificate is None:
        return

    certificate_used = (
        type(measure_condition)
        .objects.approved()
        .with_workbasket(measure_condition.workbasket)
        .exclude(pk=measure_condition.pk if measure_condition.pk else None)
        .filter(
            condition_code__code=measure_condition.condition_code.code,
            required_certificate__sid=measure_condition.required_certificate.sid,
            required_certificate__certificate_type__sid=measure_condition.required_certificate.certificate_type.sid,
            dependent_measure__sid=measure_condition.dependent_measure.sid,
        )
        .exists()
    )

    if certificate_used:
        raise ValidationError(
            "The same certificate can only be used once by the same measure and the "
            "same condition type."
        )


def validate_measure_condition_monetary_unit_validity_spans_measure_validity(
    measure_condition,
):
    """ME61"""

    if measure_condition.monetary_unit is None:
        return

    if not validity_range_contains_range(
        measure_condition.monetary_unit.valid_between,
        measure_condition.dependent_measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the referenced monetary unit must span the validity "
            "period of the measure."
        )


def validate_geo_area_only_excluded_from_groups(exclusion):
    """ME65"""

    if exclusion.modified_measure.geographical_area.area_code != AreaCode.GROUP:
        raise ValidationError(
            "An exclusion can only be entered if the measure is applicable to a "
            "geographical area group."
        )


def validate_excluded_geo_area_must_be_member_of_group(exclusion):
    """ME66"""

    geo_group = exclusion.modified_measure.geographical_area

    if not geo_group.memberships.filter(
        sid=exclusion.excluded_geographical_area.sid
    ).exists():
        raise ValidationError(
            "The excluded geographical area must be a member of the geographical area "
            "group."
        )


def validate_excluded_geo_area_membership_spans_measure_validity_period(exclusion):
    """ME67"""

    geo_group = exclusion.modified_measure.geographical_area
    excluded = exclusion.excluded_geographical_area
    membership = geo_group.members.get(member=excluded)

    if not validity_range_contains_range(
        membership.valid_between,
        exclusion.modified_measure.valid_between,
    ):
        raise ValidationError(
            "The membership period of the excluded geographical area must span the "
            "validity period of the measure."
        )


def validate_excluded_geo_area_only_once(exclusion):
    """ME68"""

    if (
        type(exclusion)
        .objects.filter(
            excluded_geographical_area__sid=exclusion.excluded_geographical_area.sid,
            modified_measure__sid=exclusion.modified_measure.sid,
        )
        .exists()
    ):
        raise ValidationError(
            "The same geographical area can only be excluded once by the same measure"
        )


def validate_footnote_only_associated_with_measure_once(
    association,
):
    """ME70"""

    footnote_used = (
        type(association)
        .objects.approved()
        .with_workbasket(association.workbasket)
        .exclude(pk=association.pk if association.pk else None)
        .filter(
            footnoted_measure__sid=association.footnoted_measure.sid,
            associated_footnote__footnote_id=association.associated_footnote.footnote_id,
            associated_footnote__footnote_type__footnote_type_id=association.associated_footnote.footnote_type.footnote_type_id,
        )
        .exists()
    )

    if footnote_used:
        raise ValidationError(
            "The same footnote can only be associated once with the same measure."
        )


def validate_cn_measures_footnote_not_used_with_taric_code(association):
    """ME71"""

    measure = association.footnoted_measure
    if measure.goods_nomenclature is None:
        return

    commodity_code = measure.goods_nomenclature.item_id

    is_taric_code = len(commodity_code) <= 8 or commodity_code[8:] != "00"
    application_code = association.associated_footnote.footnote_type.application_code

    if is_taric_code and application_code == ApplicationCode.CN_MEASURES:
        raise ValidationError(
            "Footnotes with a footnote type for which the application type = "
            '"CN footnotes" cannot be associated with TARIC codes (codes with pos. '
            "9-10 different from 00)"
        )


def validate_footnote_validity_spans_measure_validity(
    association,
):
    """ME73"""

    if not validity_range_contains_range(
        association.associated_footnote.valid_between,
        association.footnoted_measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the associated footnote must span the validity "
            "period of the measure."
        )


def validate_regulation_validity_spans_measure_validity(measure):
    """ME87"""

    if not validity_range_contains_range(
        measure.generating_regulation.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the measure (implicit or explicit) must reside "
            "within the effective validity period of its supporting regulation."
        )


def validate_goods_code_level_within_measure_type_explosion_level(measure):
    """ME88"""

    if not measure.goods_nomenclature:
        return

    goods = type(measure.goods_nomenclature).objects.filter(
        sid=measure.goods_nomenclature.sid,
        valid_between__overlap=measure.valid_between,
    )

    for good in goods:
        indents = good.indents.filter(
            valid_between__overlap=measure.valid_between,
        ).prefetch_related()

        depths = [indent.nodes.first().depth for indent in indents]

        # one level of tree depth corresponds to an increment of 2 in explosion level
        if any(
            depth * 2 > measure.measure_type.measure_explosion_level for depth in depths
        ):
            raise ValidationError(
                "The level of the goods code cannot exceed the explosion level of the "
                "measure type."
            )


def validate_terminating_regulation(measure):
    """ME104"""

    generating = measure.generating_regulation
    terminating = measure.terminating_regulation

    if terminating is None:
        return

    if generating.approved and not terminating.approved:
        raise ValidationError(
            "If the measure's measure-generating regulation is 'approved', then so "
            "must be the justification regulation."
        )

    if (
        terminating.regulation_id == generating.regulation_id
        and terminating.role_type == generating.role_type
    ):
        return

    delta = terminating.valid_between.lower - measure.valid_between.upper
    if timedelta() < delta <= timedelta(days=1):
        return

    raise ValidationError(
        "The justification regulation must be either the measure's measure-generating "
        "regulation, or a measure-generating regulation valid on the day after the "
        "measure's end date."
    )


def validate_measure_condition_component_duty_expression_only_used_once_per_condition(
    component,
):
    """ME108"""

    duty_expression_used = (
        type(component)
        .objects.approved()
        .with_workbasket(component.workbasket)
        .exclude(pk=component.pk if component.pk else None)
        .filter(
            condition__sid=component.condition.sid,
            duty_expression__sid=component.duty_expression.sid,
        )
        .exists()
    )

    if duty_expression_used:
        raise ValidationError(
            "The same duty expression can only be used once within condition components "
            "of the same condition of the same measure."
        )


def validate_additional_code_validity_spans_measure_validity(measure):
    """ME115"""

    if measure.additional_code is None:
        return

    if measure.additional_code and not validity_range_contains_range(
        measure.additional_code.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the referenced additional code must span the "
            "validity period of the measure."
        )


def validate_order_number_validity_spans_measure_validity(measure):
    """ME116

    This rule is only applicable for measures with start date after 31/12/2007."""

    if measure.valid_between.lower < datetime(2008, 1, 1, tzinfo=timezone.utc):
        return

    if measure.order_number is None:
        return

    if not validity_range_contains_range(
        measure.order_number.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the quota order number must span the "
            "validity period of the measure."
        )


def validate_quota_measure_origin_must_be_order_number_origin(measure):
    """ME117

    This rule is only applicable for measures with start date after 31/12/2007.

    Quota measure types are the following:
        122 - Non preferential tariff quota
        123 - Non preferential tariff quota under end-use
        143 - Preferential tariff quota
        146 - Preferential tariff quota under end-use
        147 - Customs Union Quota

    Only origins for quota order numbers managed by the first come first served
    principle are in scope
    """

    if measure.valid_between.lower < datetime(2008, 1, 1, tzinfo=timezone.utc):
        return

    if measure.order_number is None:
        return

    if measure.order_number.mechanism != AdministrationMechanism.FCFS:
        return

    # check the measure geo area exists as a quota order number origin (and is not
    # excluded)
    origin = measure.order_number.origins.filter(sid=measure.geographical_area.sid)
    if origin.exists() and (
        not origin.get()
        .quotaordernumberorigin_set.filter(
            excluded_areas__sid=measure.geographical_area.sid
        )
        .exists()
    ):
        return

    raise ValidationError(
        "When a measure has a quota measure type then the origin must exist as a "
        "quota order number origin."
    )


def validate_order_number_origin_validity_spans_measure_validity(measure):
    """ME119

    This rule is only applicable for measures with start date after 31/12/2007
    """

    if measure.valid_between.lower < datetime(2008, 1, 1, tzinfo=timezone.utc):
        return

    if not measure.order_number:
        return

    origin = measure.order_number.quotaordernumberorigin_set.approved().get()
    if not validity_range_contains_range(
        origin.valid_between,
        measure.valid_between,
    ):
        raise ValidationError(
            "The validity period of the quota order number origin must span the "
            "validity period of the measure."
        )
