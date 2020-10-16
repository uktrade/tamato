from datetime import datetime
from datetime import timezone
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import DataError
from django.db import IntegrityError
from psycopg2.extras import DateTimeTZRange

from common.tests import factories
from common.tests.util import only_applicable_after
from common.tests.util import requires_export_refund_nomenclature
from common.tests.util import requires_meursing_tables
from common.tests.util import requires_partial_temporary_stop
from common.validators import ApplicabilityCode
from common.validators import UpdateType
from footnotes.validators import ApplicationCode
from geo_areas.validators import AreaCode
from measures.validators import OrderNumberCaptureCode
from quotas.validators import AdministrationMechanism
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_MTS1(unique_identifying_fields):
    """The measure type series must be unique."""

    assert unique_identifying_fields(factories.MeasureTypeSeriesFactory)


def test_MTS2():
    """The measure type series cannot be deleted if it is associated with a measure
    type.
    """

    with pytest.raises(IntegrityError):
        factories.MeasureTypeFactory().measure_type_series.delete()


def test_MTS3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureTypeSeriesFactory(valid_between=date_ranges.backwards)


def test_MT1(unique_identifying_fields):
    """The measure type code must be unique."""

    assert unique_identifying_fields(factories.MeasureTypeFactory)


def test_MT2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureTypeFactory(valid_between=date_ranges.backwards)


def test_MT3(validity_period_contained):
    """When a measure type is used in a measure then the validity period of the measure
    type must span the validity period of the measure.
    """

    assert validity_period_contained(
        "measure_type", factories.MeasureTypeFactory, factories.MeasureFactory
    )


def test_MT7(date_ranges):
    """A measure type can not be deleted if it is used in a measure."""

    with pytest.raises(IntegrityError):
        factories.MeasureFactory().measure_type.delete()


def test_MT10(validity_period_contained):
    """The validity period of the measure type series must span the validity period of
    the measure type.
    """

    assert validity_period_contained(
        "measure_type_series",
        factories.MeasureTypeSeriesFactory,
        factories.MeasureTypeFactory,
    )


def test_MC1(unique_identifying_fields):
    """The code of the measure condition code must be unique."""

    assert unique_identifying_fields(factories.MeasureConditionCodeFactory)


def test_MC2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureConditionCodeFactory(valid_between=date_ranges.backwards)


def test_MC3(date_ranges):
    """If a measure condition code is used in a measure then the validity period of the
    measure condition code must span the validity period of the measure.
    """

    with pytest.raises(ValidationError):
        factories.MeasureConditionFactory(
            condition_code__valid_between=date_ranges.starts_with_normal,
            dependent_measure__valid_between=date_ranges.normal,
        )


def test_MC4():
    """The measure condition code cannot be deleted if it is used in a measure condition
    component.
    """

    with pytest.raises(IntegrityError):
        factories.MeasureConditionComponentFactory().condition.condition_code.delete()


def test_MA1(unique_identifying_fields):
    """The code of the measure action must be unique."""

    assert unique_identifying_fields(factories.MeasureActionFactory)


def test_MA2():
    """The measure action can not be deleted if it is used in a measure condition
    component.
    """

    with pytest.raises(IntegrityError):
        factories.MeasureConditionComponentFactory().condition.action.delete()


def test_MA3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureActionFactory(valid_between=date_ranges.backwards)


def test_MA4(date_ranges):
    """If a measure action is used in a measure then the validity period of the measure
    action must span the validity period of the measure.
    """

    with pytest.raises(ValidationError):
        factories.MeasureConditionFactory(
            action__valid_between=date_ranges.starts_with_normal,
            dependent_measure__valid_between=date_ranges.normal,
        )


def test_ME1(unique_identifying_fields):
    """The combination of measure type + geographical area + goods nomenclature item id
    + additional code type + additional code + order number + reduction indicator +
    start date must be unique.
    """

    assert unique_identifying_fields(factories.MeasureFactory)


@pytest.mark.skip(reason="Duplicates MT3")
def test_ME3():
    """The validity period of the measure type must span the validity period of the
    measure.
    """


def test_ME5(validity_period_contained):
    """The validity period of the geographical area must span the validity period of the
    measure.
    """

    assert validity_period_contained(
        "geographical_area", factories.GeographicalAreaFactory, factories.MeasureFactory
    )


def test_ME7():
    """The goods nomenclature code must be a product code; that is, it may not be an
    intermediate line.
    """

    with pytest.raises(ValidationError):
        factories.MeasureFactory(goods_nomenclature__suffix="00")

    factories.MeasureFactory(goods_nomenclature__suffix="80")


def test_ME8(validity_period_contained):
    """The validity period of the goods code must span the validity period of the
    measure.
    """

    assert validity_period_contained(
        "goods_nomenclature",
        factories.GoodsNomenclatureFactory,
        factories.MeasureFactory,
    )


def test_ME9():
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

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            additional_code=None,
            goods_nomenclature=None,
        )

    factories.MeasureFactory(
        additional_code=None,
        goods_nomenclature=factories.GoodsNomenclatureFactory(),
    )

    assoc = factories.AdditionalCodeTypeMeasureTypeFactory()
    additional_code = factories.AdditionalCodeFactory(type=assoc.additional_code_type)

    factories.MeasureFactory(
        additional_code=additional_code,
        goods_nomenclature=None,
        measure_type=assoc.measure_type,
    )

    factories.MeasureFactory(
        additional_code=additional_code,
        goods_nomenclature=factories.GoodsNomenclatureFactory(),
        measure_type=assoc.measure_type,
    )


def test_ME10(approved_workbasket):
    """The order number must be specified if the "order number flag" (specified in the
    measure type record) has the value "mandatory". If the flag is set to "not
    permitted" then the field cannot be entered.
    """

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
            order_number=None,
        )

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            measure_type__order_number_capture_code=OrderNumberCaptureCode.NOT_PERMITTED,
            order_number=factories.QuotaOrderNumberFactory(
                workbasket=approved_workbasket
            ),
        )


def test_ME12():
    """If the additional code is specified then the additional code type must have a
    relationship with the measure type.
    """

    with pytest.raises(ValidationError):
        factories.MeasureFactory(additional_code=factories.AdditionalCodeFactory())

    rel = factories.AdditionalCodeTypeMeasureTypeFactory()

    factories.MeasureFactory(
        measure_type=rel.measure_type,
        additional_code__type=rel.additional_code_type,
    )


@requires_meursing_tables
def test_ME13():
    """If the additional code type is related to a Meursing table plan then only the
    additional code can be specified: no goods code, order number or reduction
    indicator.
    """
    pytest.fail()


@requires_meursing_tables
def test_ME14():
    """If the additional code type is related to a Meursing table plan then the
    additional code must exist as a Meursing additional code.
    """
    pytest.fail()


@requires_meursing_tables
def test_ME15():
    """If the additional code type is related to a Meursing table plan then the validity
    period of the additional code must span the validity period of the measure.
    """
    pytest.fail()


def test_ME16():
    """Integrating a measure with an additional code when an equivalent or overlapping
    measures without additional code already exists and vice-versa, should be
    forbidden.
    """

    existing = factories.MeasureFactory(additional_code=None)
    additional_code = factories.AdditionalCodeFactory()

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            measure_type=existing.measure_type,
            geographical_area=existing.geographical_area,
            goods_nomenclature=existing.goods_nomenclature,
            additional_code=additional_code,
            order_number=existing.order_number,
            reduction=existing.reduction,
        )

    existing.additional_code = additional_code
    factories.AdditionalCodeTypeMeasureTypeFactory(
        measure_type=existing.measure_type,
        additional_code_type=additional_code.type,
    )
    existing.save()

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            measure_type=existing.measure_type,
            geographical_area=existing.geographical_area,
            goods_nomenclature=existing.goods_nomenclature,
            additional_code=None,
            order_number=existing.order_number,
            reduction=existing.reduction,
        )


def test_ME17(must_exist):
    """If the additional code type has as application "non-Meursing" then the additional
    code must exist as a non-Meursing additional code.

    UK tariff does not use meursing tables, so this is essentially saying that an
    additional code must exist.
    """

    assert must_exist(
        "additional_code", factories.AdditionalCodeFactory, factories.MeasureFactory
    )


@pytest.mark.skip(reason="No meursing, so duplicate of ME115")
def test_ME18():
    """If the additional code type has as application "non-Meursing" then the validity
    period of the non-Meursing additional code must span the validity period of the
    measure.
    """


@requires_export_refund_nomenclature
def test_ME19():
    """If the additional code type has as application "ERN" then the goods code must be
    specified but the order number is blocked for input.
    """
    pytest.fail()


@requires_export_refund_nomenclature
def test_ME21():
    """If the additional code type has as application "ERN" then the combination of
    goods code + additional code must exist as an ERN product code and its validity
    period must span the validity period of the measure.
    """
    pytest.fail()


def test_ME24(must_exist):
    """The role + regulation id must exist. If no measure start date is specified it
    defaults to the regulation start date.
    """

    assert must_exist(
        "generating_regulation", factories.RegulationFactory, factories.MeasureFactory
    )


def test_ME25(date_ranges):
    """If the measure’s end date is specified (implicitly or explicitly) then the start
    date of the measure must be less than or equal to the end date.

    End date will in almost all circumstances be null for measures.
    """

    with pytest.raises(DataError):
        factories.MeasureFactory(valid_between=date_ranges.backwards)


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used"
)
def test_ME26():
    """The entered regulation may not be completely abrogated."""


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used"
)
def test_ME27():
    """The entered regulation may not be fully replaced."""


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used"
)
def test_ME28():
    """The entered regulation may not be partially replaced for the measure type,
    geographical area or chapter (first two digits of the goods code) of the measure.
    """


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used"
)
def test_ME29():
    """If the entered regulation is a modification regulation then its base regulation
    may not be completely abrogated.
    """


def test_ME32(approved_workbasket, date_ranges):
    """There may be no overlap in time with other measure occurrences with a goods code
    in the same nomenclature hierarchy which references the same measure type, geo area,
    order number, additional code and reduction indicator. This rule is not applicable
    for Meursing additional codes.

    This is an extension of the previously described ME1 to all commodity codes in the
    upward hierarchy and all commodity codes in the downward hierarchy.
    """

    existing = factories.MeasureFactory(
        goods_nomenclature__indent__workbasket=approved_workbasket,
        goods_nomenclature__workbasket=approved_workbasket,
        measure_type__measure_explosion_level=10,
        measure_type__measure_component_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        workbasket=approved_workbasket,
    )

    measure = factories.MeasureFactory(
        goods_nomenclature__origin=factories.GoodsNomenclatureFactory(
            valid_between=date_ranges.adjacent_earlier,
        ),
        goods_nomenclature__indent__parent=existing.goods_nomenclature.indents.first(),
        measure_type=existing.measure_type,
        geographical_area=existing.geographical_area,
        order_number=existing.order_number,
        additional_code=existing.additional_code,
        reduction=existing.reduction,
    )

    with pytest.raises(ValidationError):
        measure.workbasket.submit_for_approval()


def test_ME33(date_ranges):
    """A justification regulation may not be entered if the measure end date is not
    filled in.

    A justification regulation is used to ‘justify’ terminating a regulation. There is
    no requirement for this in UK law, nor for audit purposes in the UK tariff, however
    it is a mandatory field in the database and in CDS. The rule is self-explanatory: if
    there no end date on the measure, then the justification regulation field must be
    set to null.
    """

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            valid_between=date_ranges.no_end,
            terminating_regulation=factories.RegulationFactory(),
        )


def test_ME34(date_ranges):
    """A justification regulation must be entered if the measure end date is filled
    in.

    The justification regulation fields MUST be completed when the regulation is end-dated.
    - Users should be discouraged from end dating regulations, instead they should end
      date measures.
    - Always use the measure generating regulation ID and role to populate the
      justification equivalents, if the end date needs to be entered on a regulation.
    """

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            valid_between=date_ranges.normal,
            terminating_regulation=None,
        )


@requires_partial_temporary_stop
def test_ME39():
    """The validity period of the measure must span the validity period of all related
    partial temporary stop (PTS) records."""
    pytest.fail()


def test_ME40():
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

    measure = factories.MeasureFactory(
        measure_type__measure_component_applicability_code=ApplicabilityCode.MANDATORY,
    )
    with pytest.raises(ValidationError):
        measure.workbasket.submit_for_approval()

    measure = factories.MeasureFactory(
        measure_type__measure_component_applicability_code=ApplicabilityCode.NOT_PERMITTED,
    )
    factories.MeasureComponentFactory(
        component_measure=measure, workbasket=measure.workbasket
    )
    with pytest.raises(ValidationError):
        measure.workbasket.submit_for_approval()

    measure = factories.MeasureFactory(
        measure_type__measure_component_applicability_code=ApplicabilityCode.NOT_PERMITTED,
    )
    factories.MeasureConditionComponentFactory(
        condition__dependent_measure=measure,
        workbasket=measure.workbasket,
    )
    with pytest.raises(ValidationError):
        measure.workbasket.submit_for_approval()

    measure = factories.MeasureFactory(
        measure_type__measure_component_applicability_code=ApplicabilityCode.MANDATORY,
    )
    factories.MeasureComponentFactory(
        component_measure=measure,
        workbasket=measure.workbasket,
    )
    factories.MeasureConditionComponentFactory(
        condition__dependent_measure=measure,
        workbasket=measure.workbasket,
    )
    with pytest.raises(ValidationError):
        measure.workbasket.submit_for_approval()


def test_ME41(must_exist):
    """The referenced duty expression must exist."""

    assert must_exist(
        "duty_expression",
        factories.DutyExpressionFactory,
        factories.MeasureComponentFactory,
    )


def test_ME42(date_ranges):
    """The validity period of the duty expression must span the validity period of the
    measure."""

    with pytest.raises(ValidationError):
        factories.MeasureComponentFactory(
            duty_expression__valid_between=date_ranges.starts_with_normal,
            component_measure__valid_between=date_ranges.normal,
        )


def test_ME43(approved_workbasket):
    """The same duty expression can only be used once with the same measure.

    Even if an expression that (in English) reads the same needs to be used more than
    once in a measure, we must use a different expression ID, never the same one twice.
    """

    existing = factories.MeasureComponentFactory(workbasket=approved_workbasket)

    with pytest.raises(ValidationError):
        factories.MeasureComponentFactory(
            duty_expression=existing.duty_expression,
            component_measure=existing.component_measure,
        )


def test_ME45(component_applicability):
    """If the flag "amount" on duty expression is "mandatory" then an amount must be
    specified. If the flag is set "not permitted" then no amount may be entered."""

    assert component_applicability("duty_amount", Decimal(1))


def test_ME46(component_applicability):
    """If the flag "monetary unit" on duty expression is "mandatory" then a monetary
    unit must be specified. If the flag is set "not permitted" then no monetary unit may
    be entered."""

    assert component_applicability("monetary_unit", factories.MonetaryUnitFactory())


def test_ME47(component_applicability):
    """If the flag "measurement unit" on duty expression is "mandatory" then a
    measurement unit must be specified. If the flag is set "not permitted" then no
    measurement unit may be entered.
    """

    assert component_applicability(
        "component_measurement",
        factories.MeasurementFactory(),
        applicability_field="duty_expression__measurement_unit_applicability_code",
    )


def test_ME48(must_exist):
    """The referenced monetary unit must exist."""

    assert must_exist(
        "monetary_unit",
        factories.MonetaryUnitFactory,
        factories.MeasureComponentFactory,
    )


def test_ME49(date_ranges):
    """The validity period of the referenced monetary unit must span the validity period
    of the measure."""

    with pytest.raises(ValidationError):
        factories.MeasureComponentFactory(
            monetary_unit=factories.MonetaryUnitFactory(
                valid_between=date_ranges.starts_with_normal
            ),
            component_measure__valid_between=date_ranges.normal,
        )


def test_ME50(must_exist):
    """The combination measurement unit + measurement unit qualifier must exist."""

    assert must_exist(
        "component_measurement",
        factories.MeasurementFactory,
        factories.MeasureComponentFactory,
    )


def test_ME51(date_ranges):
    """The validity period of the measurement unit must span the validity period of the
    measure."""

    with pytest.raises(ValidationError):
        factories.MeasureComponentFactory(
            component_measurement=factories.MeasurementFactory(
                measurement_unit__valid_between=date_ranges.starts_with_normal
            ),
            component_measure__valid_between=date_ranges.normal,
        )


def test_ME52(date_ranges):
    """The validity period of the measurement unit qualifier must span the validity
    period of the measure."""

    with pytest.raises(ValidationError):
        factories.MeasureComponentFactory(
            component_measurement=factories.MeasurementFactory(
                measurement_unit_qualifier__valid_between=date_ranges.starts_with_normal
            ),
            component_measure__valid_between=date_ranges.normal,
        )


def test_ME53(must_exist):
    """The referenced measure condition must exist."""

    assert must_exist(
        "condition",
        factories.MeasureConditionFactory,
        factories.MeasureConditionComponentFactory,
    )


@pytest.mark.skip(reason="Erroneous business rule")
def test_ME54(date_ranges):
    """The validity period of the referenced measure condition must span the validity
    period of the measure.

    Not required - disregard: as far as we can see, this is an erroneous business rule.
    The measure condition table does not have a start and end date field. The condition
    adopts the start and end dates of the parent measure. Similarly, there are no start
    and end dates associated with a measure condition component (or for that matter a
    measure component).  They all adopt the date constraints of the parent measure.
    """


@pytest.mark.skip(reason="Erroneous business rule")
def test_ME55():
    """A measure condition refers to a measure condition or to a condition + certificate
    or to a condition + amount specifications.

    Disregard: this has been written so vaguely that there are no rules to be gleaned
    from it.
    """


def test_ME56(must_exist):
    """The referenced certificate must exist."""

    assert must_exist(
        "required_certificate",
        factories.CertificateFactory,
        factories.MeasureConditionFactory,
    )


def test_ME57(date_ranges):
    """The validity period of the referenced certificate must span the validity period
    of the measure."""

    with pytest.raises(ValidationError):
        factories.MeasureConditionFactory(
            required_certificate=factories.CertificateFactory(
                valid_between=date_ranges.starts_with_normal
            ),
            dependent_measure__valid_between=date_ranges.normal,
        )


def test_ME58(approved_workbasket):
    """The same certificate can only be referenced once by the same measure and the same
    condition type."""

    existing = factories.MeasureConditionFactory(
        required_certificate=factories.CertificateFactory(),
        workbasket=approved_workbasket,
    )

    with pytest.raises(ValidationError):
        factories.MeasureConditionFactory(
            condition_code=existing.condition_code,
            dependent_measure=existing.dependent_measure,
            required_certificate=existing.required_certificate,
        )


def test_ME59(must_exist):
    """The referenced action code must exist."""

    assert must_exist(
        "action",
        factories.MeasureActionFactory,
        factories.MeasureConditionFactory,
    )


def test_ME60(must_exist):
    """The referenced monetary unit must exist."""

    assert must_exist(
        "monetary_unit",
        factories.MonetaryUnitFactory,
        factories.MeasureConditionFactory,
    )


def test_ME61(date_ranges):
    """The validity period of the referenced monetary unit must span the validity period
    of the measure."""

    with pytest.raises(ValidationError):
        factories.MeasureConditionFactory(
            monetary_unit=factories.MonetaryUnitFactory(
                valid_between=date_ranges.starts_with_normal
            ),
            dependent_measure__valid_between=date_ranges.normal,
        )


def test_ME62(must_exist):
    """The combination measurement unit + measurement unit qualifier must exist."""

    assert must_exist(
        "condition_measurement",
        factories.MeasurementFactory,
        factories.MeasureConditionFactory,
    )


def test_ME63(date_ranges):
    """The validity period of the measurement unit must span the validity period of the
    measure."""

    with pytest.raises(ValidationError):
        factories.MeasureConditionFactory(
            condition_measurement=factories.MeasurementFactory(
                measurement_unit__valid_between=date_ranges.starts_with_normal
            ),
            dependent_measure__valid_between=date_ranges.normal,
        )


def test_ME64(date_ranges):
    """The validity period of the measurement unit qualifier must span the validity
    period of the measure."""

    with pytest.raises(ValidationError):
        factories.MeasureConditionFactory(
            condition_measurement=factories.MeasurementFactory(
                measurement_unit_qualifier__valid_between=date_ranges.starts_with_normal
            ),
            dependent_measure__valid_between=date_ranges.normal,
        )


def test_ME65():
    """An exclusion can only be entered if the measure is applicable to a geographical
    area group (area code = 1)."""

    measure = factories.MeasureFactory(geographical_area__area_code=AreaCode.COUNTRY)

    with pytest.raises(ValidationError):
        factories.MeasureExcludedGeographicalAreaFactory(
            modified_measure=measure,
        )


def test_ME66():
    """The excluded geographical area must be a member of the geographical area group."""

    membership = factories.GeographicalMembershipFactory()
    measure = factories.MeasureFactory(geographical_area=membership.geo_group)

    with pytest.raises(ValidationError):
        factories.MeasureExcludedGeographicalAreaFactory(
            modified_measure=measure,
            excluded_geographical_area=factories.GeographicalAreaFactory(),
        )

    factories.MeasureExcludedGeographicalAreaFactory(
        modified_measure=measure,
        excluded_geographical_area=membership.member,
    )


def test_ME67(date_ranges):
    """The membership period of the excluded geographical area must span the validity
    period of the measure."""

    membership = factories.GeographicalMembershipFactory(
        valid_between=date_ranges.starts_with_normal,
    )

    with pytest.raises(ValidationError):
        factories.MeasureExcludedGeographicalAreaFactory(
            excluded_geographical_area=membership.member,
            modified_measure__geographical_area=membership.geo_group,
            modified_measure__valid_between=date_ranges.normal,
        )


def test_ME68():
    """The same geographical area can only be excluded once by the same measure."""

    membership = factories.GeographicalMembershipFactory()

    existing = factories.MeasureExcludedGeographicalAreaFactory(
        excluded_geographical_area=membership.member,
        modified_measure__geographical_area=membership.geo_group,
    )

    with pytest.raises(ValidationError):
        factories.MeasureExcludedGeographicalAreaFactory(
            excluded_geographical_area=existing.excluded_geographical_area,
            modified_measure=existing.modified_measure,
        )


# Footnote association
def test_ME69(must_exist):
    """The associated footnote must exist."""

    assert must_exist(
        "associated_footnote",
        factories.FootnoteFactory,
        factories.FootnoteAssociationMeasureFactory,
    )


def test_ME70(approved_workbasket):
    """The same footnote can only be associated once with the same measure."""

    existing = factories.FootnoteAssociationMeasureFactory(
        workbasket=approved_workbasket,
    )

    with pytest.raises(ValidationError):
        factories.FootnoteAssociationMeasureFactory(
            footnoted_measure=existing.footnoted_measure,
            associated_footnote=existing.associated_footnote,
        )


def test_ME71():
    """Footnotes with a footnote type for which the application type = "CN footnotes"
    cannot be associated with TARIC codes (codes with pos. 9-10 different from 00)"""

    with pytest.raises(ValidationError):
        factories.FootnoteAssociationMeasureFactory(
            associated_footnote__footnote_type__application_code=ApplicationCode.CN_MEASURES,
            footnoted_measure__goods_nomenclature=factories.GoodsNomenclatureFactory(
                item_id="0123456789",
            ),
        )


def test_ME72():
    """Footnotes with a footnote type for which the application type = "measure
    footnotes" can be associated at any level.

    This refers to footnotes of type PB, IS, CD, MX, TM, EU, CG, TR, CO, OZ, MG, which
    have an application code of “7”.
    """

    factories.FootnoteAssociationMeasureFactory(
        associated_footnote__footnote_type__application_code=ApplicationCode.OTHER_MEASURES,
        footnoted_measure__goods_nomenclature=factories.GoodsNomenclatureFactory(
            item_id="0123456789",
        ),
    )


def test_ME73(date_ranges):
    """The validity period of the associated footnote must span the validity period of
    the measure."""

    with pytest.raises(ValidationError):
        factories.FootnoteAssociationMeasureFactory(
            associated_footnote__valid_between=date_ranges.starts_with_normal,
            footnoted_measure__valid_between=date_ranges.normal,
        )


@requires_partial_temporary_stop
def test_ME74():
    """The start date of the PTS must be less than or equal to the end date."""
    pytest.fail()


@requires_partial_temporary_stop
def test_ME75():
    """The PTS regulation and abrogation regulation must be the same if the start date
    and the end date are entered when creating the record."""
    pytest.fail()


@requires_partial_temporary_stop
def test_ME76():
    """The abrogation regulation may not be entered if the PTS end date is not filled
    in."""
    pytest.fail()


@requires_partial_temporary_stop
def test_ME77():
    """The abrogation regulation must be entered if the PTS end date is filled in."""
    pytest.fail()


@requires_partial_temporary_stop
def test_ME78():
    """The abrogation regulation must be different from the PTS regulation if the end
    date is filled in during a modification."""
    pytest.fail()


@requires_partial_temporary_stop
def test_ME79():
    """There may be no overlap between different PTS periods."""
    pytest.fail()


@pytest.mark.skip(reason="All UK tariff regulations are Base regulations")
def test_ME86():
    """The role of the entered regulation must be a Base, a Modification, a Provisional
    Anti- Dumping, a Definitive Anti-Dumping.
    """


def test_ME87(date_ranges):
    """The validity period of the measure (implicit or explicit) must reside within the
    effective validity period of its supporting regulation. The effective validity
    period is the validity period of the regulation taking into account extensions and
    abrogation.

    A regulation’s validity period is hugely complex in the EU’s world.
    - A regulation is initially assigned a start date. It may be assigned an end date as
      well at the point of creation but this is rare.
    - The EU then may choose to end date the regulation using its end date field – in
      this case provision must be made to end date all of the measures that would
      otherwise extend beyond the end of this regulation end date.
    - The EU may also choose to end date the measure via 2 other means which we are
      abandoning (abrogation and prorogation).
    - Only the measure validity end date and the regulation validity end date field will
      need to be compared in the UK Tariff. However, in terminating measures from the EU
      tariff to make way for UK equivalents, and to avoid data clashes such as ME32, we DO
      need to be aware of this multiplicity of end dates.
    """

    # explicit
    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            generating_regulation__valid_between=date_ranges.starts_with_normal,
            valid_between=date_ranges.normal,
        )

    # implicit - regulation end date supercedes measure end date
    # generating reg:  s---x
    # measure:         s---i----x       i = implicit end date
    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            generating_regulation__valid_between=date_ranges.starts_with_normal,
            valid_between=date_ranges.normal,
        )


def test_ME88(date_ranges, approved_workbasket):
    """The level of the goods code, if present, cannot exceed the explosion level of the
    measure type.
    """

    mt = factories.MeasureTypeFactory(measure_explosion_level=2)
    good = factories.GoodsNomenclatureFactory.build(workbasket=approved_workbasket)
    good.save()
    factories.GoodsNomenclatureIndentFactory(indented_goods_nomenclature=good, depth=2)

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            measure_type=mt,
            goods_nomenclature=good,
            valid_between=date_ranges.normal,
        )


def test_ME104(date_ranges):
    """The justification regulation must be either:
        - the measure’s measure-generating regulation, or
        - a measure-generating regulation, valid on the day after the measure’s
          (explicit) end date.
    If the measure’s measure-generating regulation is ‘approved’, then so must be the
    justification regulation.
    """

    measure = factories.MeasureFactory(valid_between=date_ranges.normal)
    generating = measure.generating_regulation
    terminating = measure.terminating_regulation

    assert (
        terminating.regulation_id == generating.regulation_id
        and terminating.role_type == generating.role_type
    )

    measure.terminating_regulation = factories.RegulationFactory(
        valid_between=DateTimeTZRange(
            measure.valid_between.upper + relativedelta(days=+1),
            None,
        ),
    )
    measure.save()

    measure.terminating_regulation = factories.RegulationFactory()
    with pytest.raises(ValidationError):
        measure.save()


def test_ME105(must_exist):
    """The referenced duty expression must exist."""

    assert must_exist(
        "duty_expression",
        factories.DutyExpressionFactory,
        factories.MeasureConditionComponentFactory,
    )


def test_ME106(date_ranges):
    """The validity period of the duty expression must span the validity period of the
    measure.
    """

    with pytest.raises(ValidationError):
        factories.MeasureConditionComponentFactory(
            duty_expression__valid_between=date_ranges.starts_with_normal,
            condition__dependent_measure__valid_between=date_ranges.normal,
        )


def test_ME108(approved_workbasket):
    """The same duty expression can only be used once within condition components of the
    same condition of the same measure.  (i.e. it can be re-used in other conditions, no
    matter what condition type, of the same measure)
    """

    existing = factories.MeasureConditionComponentFactory(
        workbasket=approved_workbasket
    )

    with pytest.raises(ValidationError):
        factories.MeasureConditionComponentFactory(
            duty_expression=existing.duty_expression,
            condition=existing.condition,
        )


def test_ME109(component_applicability):
    """If the flag 'amount' on duty expression is 'mandatory' then an amount must be
    specified. If the flag is set to 'not permitted' then no amount may be entered.
    """

    assert component_applicability(
        "duty_amount", Decimal(1), factory=factories.MeasureConditionComponentFactory
    )


def test_ME110(component_applicability):
    """If the flag 'monetary unit' on duty expression is 'mandatory' then a monetary
    unit must be specified. If the flag is set to 'not permitted' then no monetary unit
    may be entered.
    """

    assert component_applicability(
        "monetary_unit",
        factories.MonetaryUnitFactory(),
        factory=factories.MeasureConditionComponentFactory,
    )


def test_ME111(component_applicability):
    """If the flag 'measurement unit' on duty expression is 'mandatory' then a
    measurement unit must be specified. If the flag is set to 'not permitted' then no
    measurement unit may be entered.
    """

    assert component_applicability(
        "condition_component_measurement",
        factories.MeasurementFactory(),
        factory=factories.MeasureConditionComponentFactory,
        applicability_field="duty_expression__measurement_unit_applicability_code",
    )


@requires_export_refund_nomenclature
def test_ME112():
    """If the additional code type has as application "Export Refund for Processed
    Agricultural Goods" then the measure does not require a goods code.
    """
    pytest.fail()


@requires_export_refund_nomenclature
def test_ME113():
    """If the additional code type has as application "Export Refund for Processed
    Agricultural Goods" then the additional code must exist as an Export Refund for
    Processed Agricultural Goods additional code.
    """
    pytest.fail()


@requires_export_refund_nomenclature
def test_ME114():
    """If the additional code type has as application "Export Refund for Processed
    Agricultural Goods" then the validity period of the Export Refund for Processed
    Agricultural Goods additional code must span the validity period of the measure.
    """
    pytest.fail()


def test_ME115(validity_period_contained):
    """The validity period of the referenced additional code must span the validity
    period of the measure
    """

    assert validity_period_contained(
        "additional_code", factories.AdditionalCodeFactory, factories.MeasureFactory
    )


@only_applicable_after("31/12/2007")
def test_ME116(date_ranges):
    """When a quota order number is used in a measure then the validity period of the
    quota order number must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            order_number=factories.QuotaOrderNumberFactory(
                valid_between=date_ranges.starts_with_normal,
            ),
            valid_between=date_ranges.normal,
            measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
        )


@only_applicable_after("31/12/2007")
def test_ME117(approved_workbasket):
    """When a measure has a quota measure type then the origin must exist as a quota
    order number origin.

    This rule is only applicable for measures with start date after 31/12/2007.

    Only origins for quota order numbers managed by the first come first served
    principle are in scope
    """

    origin = factories.QuotaOrderNumberOriginFactory(
        order_number__mechanism=AdministrationMechanism.FCFS,
        workbasket=approved_workbasket,
    )

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
            order_number=origin.order_number,
            geographical_area=factories.GeographicalAreaFactory(),
        )

    factories.MeasureFactory(
        measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
        order_number=origin.order_number,
        geographical_area=origin.geographical_area,
    )


@pytest.mark.skip(reason="Duplicate of ME116")
def test_ME118():
    """When a quota order number is used in a measure then the validity period of the
    quota order number must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """


@only_applicable_after("31/12/2007")
def test_ME119(approved_workbasket, date_ranges):
    """When a quota order number is used in a measure then the validity period of the
    quota order number origin must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
            order_number=factories.QuotaOrderNumberOriginFactory(
                valid_between=date_ranges.starts_with_normal,
                order_number__origin=None,
                workbasket=approved_workbasket,
            ).order_number,
            valid_between=date_ranges.normal,
        )
