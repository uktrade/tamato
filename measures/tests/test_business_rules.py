from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta
from django.db import DataError

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import Dates
from common.tests.util import only_applicable_after
from common.tests.util import requires_export_refund_nomenclature
from common.tests.util import requires_meursing_tables
from common.tests.util import requires_partial_temporary_stop
from common.util import TaricDateRange
from common.validators import ApplicabilityCode
from common.validators import UpdateType
from footnotes.validators import ApplicationCode
from geo_areas.validators import AreaCode
from measures import business_rules
from measures.validators import DutyExpressionId
from measures.validators import OrderNumberCaptureCode
from quotas.validators import AdministrationMechanism

pytestmark = pytest.mark.django_db


# 140 - MEASURE TYPE SERIES


def test_MTS1(make_duplicate_record):
    """The measure type series must be unique."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.MTS1().validate(
            make_duplicate_record(factories.MeasureTypeSeriesFactory),
        )


def test_MTS2(delete_record):
    """The measure type series cannot be deleted if it is associated with a
    measure type."""

    measure_type = factories.MeasureTypeFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.MTS2().validate(delete_record(measure_type.measure_type_series))


def test_MTS3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureTypeSeriesFactory.create(valid_between=date_ranges.backwards)


# 235 - MEASURE TYPE


def test_MT1(make_duplicate_record):
    """The measure type code must be unique."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.MT1().validate(
            make_duplicate_record(factories.MeasureTypeFactory),
        )


def test_MT2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureTypeFactory.create(valid_between=date_ranges.backwards)


def test_MT3(date_ranges):
    """When a measure type is used in a measure then the validity period of the
    measure type must span the validity period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.MT3().validate(
            factories.MeasureFactory.create(
                measure_type__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_MT4(reference_nonexistent_record):
    """The referenced measure type series must exist."""

    with reference_nonexistent_record(
        factories.MeasureTypeFactory,
        "measure_type_series",
    ) as measure_type:
        with pytest.raises(BusinessRuleViolation):
            business_rules.MT4().validate(measure_type)


def test_MT7(delete_record):
    """A measure type can not be deleted if it is used in a measure."""

    measure = factories.MeasureFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.MT7().validate(delete_record(measure.measure_type))


def test_MT10(date_ranges):
    """The validity period of the measure type series must span the validity
    period of the measure type."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.MT10().validate(
            factories.MeasureTypeFactory.create(
                measure_type_series__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            ),
        )


# 350 - MEASURE CONDITION CODE


def test_MC1(make_duplicate_record):
    """The code of the measure condition code must be unique."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.MC1().validate(
            make_duplicate_record(factories.MeasureConditionCodeFactory),
        )


def test_MC2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureConditionCodeFactory.create(
            valid_between=date_ranges.backwards,
        )


def test_MC3(date_ranges):
    """If a measure condition code is used in a measure then the validity period
    of the measure condition code must span the validity period of the
    measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.MC3().validate(
            factories.MeasureConditionFactory.create(
                condition_code__valid_between=date_ranges.normal,
                dependent_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


def test_MC4(delete_record):
    """The measure condition code cannot be deleted if it is used in a measure
    condition component."""

    component = factories.MeasureConditionComponentFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.MC4().validate(delete_record(component.condition.condition_code))


# 355 - MEASURE ACTION


def test_MA1(make_duplicate_record):
    """The code of the measure action must be unique."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.MA1().validate(
            make_duplicate_record(factories.MeasureActionFactory),
        )


def test_MA2(delete_record):
    """The measure action can not be deleted if it is used in a measure
    condition component."""

    component = factories.MeasureConditionComponentFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.MA2().validate(delete_record(component.condition.action))


def test_MA3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureActionFactory.create(valid_between=date_ranges.backwards)


def test_MA4(date_ranges):
    """If a measure action is used in a measure then the validity period of the
    measure action must span the validity period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.MA4().validate(
            factories.MeasureConditionFactory.create(
                action__valid_between=date_ranges.starts_with_normal,
                dependent_measure__valid_between=date_ranges.normal,
            ),
        )


# 430 - MEASURE


def test_ME1(make_duplicate_record):
    """
    The combination of measure type + geographical area + goods nomenclature
    item id.

    + additional code type + additional code + order number + reduction
    indicator + start date must be unique.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME1().validate(
            make_duplicate_record(
                factories.MeasureFactory,
                identifying_fields=(
                    "measure_type",
                    "geographical_area",
                    "goods_nomenclature",
                    "additional_code",
                    "order_number",
                    "reduction",
                    "valid_between__lower",
                ),
            ),
        )


def test_ME2(reference_nonexistent_record):
    """The measure type must exist."""

    with reference_nonexistent_record(
        factories.MeasureFactory,
        "measure_type",
    ) as measure:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME2().validate(measure)


def test_ME3(date_ranges):
    """The validity period of the measure type must span the validity period of
    the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME3().validate(
            factories.MeasureFactory.create(
                measure_type__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME4(reference_nonexistent_record):
    """The geographical area must exist."""

    with reference_nonexistent_record(
        factories.MeasureFactory,
        "geographical_area",
    ) as measure:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME4().validate(measure)


def test_ME5(date_ranges):
    """The validity period of the geographical area must span the validity
    period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME5().validate(
            factories.MeasureFactory.create(
                geographical_area__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME6(reference_nonexistent_record):
    """The goods code must exist."""

    def teardown(good):
        for indent in good.indents.all():
            indent.nodes.all().delete()
            indent.delete()
        good.descriptions.all().delete()
        good.origin_links.all().delete()
        good.goodsnomenclatureorigin_set.all().delete()
        good.delete()

    with reference_nonexistent_record(
        factories.MeasureFactory,
        "goods_nomenclature",
        teardown,
    ) as measure:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME6().validate(measure)


def test_ME7():
    """The goods nomenclature code must be a product code; that is, it may not
    be an intermediate line."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME7().validate(
            factories.MeasureFactory.create(goods_nomenclature__suffix="00"),
        )

    business_rules.ME7().validate(
        factories.MeasureFactory.create(goods_nomenclature__suffix="80"),
    )


def test_ME8(date_ranges):
    """The validity period of the goods code must span the validity period of
    the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME8().validate(
            factories.MeasureFactory.create(
                goods_nomenclature__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME88():
    """The level of the goods code, if present, cannot exceed the explosion
    level of the measure type."""

    good = factories.GoodsNomenclatureFactory.create(item_id="9999999900")

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME88().validate(
            factories.MeasureFactory.create(
                measure_type__measure_explosion_level=2,
                goods_nomenclature=good,
                leave_measure=True,
            ),
        )


def test_ME16():
    """Integrating a measure with an additional code when an equivalent or
    overlapping measures without additional code already exists and vice-versa,
    should be forbidden."""

    existing = factories.MeasureFactory.create(additional_code=None)
    additional_code = factories.AdditionalCodeFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME16().validate(
            factories.MeasureFactory.create(
                measure_type=existing.measure_type,
                geographical_area=existing.geographical_area,
                goods_nomenclature=existing.goods_nomenclature,
                additional_code=additional_code,
                order_number=existing.order_number,
                reduction=existing.reduction,
            ),
        )

    existing.additional_code = additional_code
    existing.save(force_write=True)

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME16().validate(
            factories.MeasureFactory.create(
                measure_type=existing.measure_type,
                geographical_area=existing.geographical_area,
                goods_nomenclature=existing.goods_nomenclature,
                additional_code=None,
                order_number=existing.order_number,
                reduction=existing.reduction,
            ),
        )


def test_ME115(date_ranges):
    """The validity period of the referenced additional code must span the
    validity period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME115().validate(
            factories.MeasureWithAdditionalCodeFactory.create(
                additional_code__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME25(date_ranges):
    """
    If the measure’s end date is specified (implicitly or explicitly) then the
    start date of the measure must be less than or equal to the end date.

    End date will in almost all circumstances be explicit for measures. If it is
    not, the implicit end date will come from the regulation. It is possible for
    the regulation to have an end date and an optional "effective end date". If
    the effective end date is present it should override the original end date.
    """

    business_rules.ME25().validate(
        factories.MeasureFactory.create(valid_between=date_ranges.normal),
    )

    business_rules.ME25().validate(
        factories.MeasureFactory.create(
            valid_between=date_ranges.no_end,
            generating_regulation__valid_between=date_ranges.earlier,
            generating_regulation__effective_end_date=None,
        ),
    )

    business_rules.ME25().validate(
        factories.MeasureFactory.create(
            valid_between=date_ranges.no_end,
            generating_regulation__valid_between=date_ranges.no_end,
            generating_regulation__effective_end_date=None,
        ),
    )

    with pytest.raises(DataError):
        factories.MeasureFactory.create(valid_between=date_ranges.backwards)

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME25().validate(
            factories.MeasureFactory.create(
                valid_between=date_ranges.no_end,
                generating_regulation__valid_between=date_ranges.earlier,
                generating_regulation__effective_end_date=date_ranges.earlier.upper,
            ),
        )


@pytest.fixture
def existing_goods_nomenclature(date_ranges):
    return factories.GoodsNomenclatureFactory(
        valid_between=date_ranges.big,
    )


def updated_goods_nomenclature(e):
    good = factories.GoodsNomenclatureFactory(
        valid_between=e.valid_between,
        indent__node__parent=e.indents.first().nodes.first(),
    )

    new_indent = factories.GoodsNomenclatureIndentFactory(
        update_type=UpdateType.UPDATE,
        version_group=good.indents.first().version_group,
        node__parent=None,
    )

    return good


@pytest.fixture(
    params=(
        (lambda e: e, True),
        (
            lambda e: factories.GoodsNomenclatureFactory(
                indent__node__parent=e.indents.first().nodes.first(),
                valid_between=e.valid_between,
            ),
            True,
        ),
        (
            updated_goods_nomenclature,
            False,
        ),
    ),
    ids=[
        "current:self",
        "current:child",
        "former:parent",
    ],
)
def related_goods_nomenclature(request, existing_goods_nomenclature):
    callable, expected = request.param
    return callable(existing_goods_nomenclature), expected


@pytest.fixture(
    params=(
        lambda d: {"valid_between": d.normal},
        lambda d: {
            "valid_between": d.no_end,
            "generating_regulation__valid_between": d.normal,
            "generating_regulation__effective_end_date": d.normal.upper,
        },
    ),
    ids=[
        "explicit",
        "implicit",
    ],
)
def existing_measure_data(request, date_ranges, existing_goods_nomenclature):
    return {
        "goods_nomenclature": existing_goods_nomenclature,
        **request.param(date_ranges),
    }


@pytest.fixture(
    params=(
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
            },
            True,
        ),
        (
            lambda d: {
                "valid_between": Dates.no_end_before(d.adjacent_earlier.lower),
                "generating_regulation__valid_between": d.adjacent_earlier,
                "generating_regulation__effective_end_date": d.adjacent_earlier.upper,
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.later,
            },
            False,
        ),
    ),
    ids=[
        "explicit:overlapping",
        "implicit:not-overlapping",
        "explicit:not-overlapping",
    ],
)
def related_measure_data(request, date_ranges, related_goods_nomenclature):
    callable, date_overlap = request.param
    nomenclature, nomenclature_overlap = related_goods_nomenclature
    return {
        "goods_nomenclature": nomenclature,
        **callable(date_ranges),
    }, date_overlap and nomenclature_overlap


def test_ME32(existing_measure_data, related_measure_data):
    """
    There may be no overlap in time with other measure occurrences with a goods
    code in the same nomenclature hierarchy which references the same measure
    type, geo area, order number, additional code and reduction indicator. This
    rule is not applicable for Meursing additional codes.

    This is an extension of the previously described ME1 to all commodity codes
    in the upward hierarchy and all commodity codes in the downward hierarchy.
    """

    existing = factories.MeasureFactory.create(**existing_measure_data)

    related_data, error_expected = related_measure_data
    related = factories.MeasureFactory.create(
        measure_type=existing.measure_type,
        geographical_area=existing.geographical_area,
        order_number=existing.order_number,
        additional_code=existing.additional_code,
        reduction=existing.reduction,
        **related_data,
    )

    if error_expected:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME32().validate(related)
    else:
        business_rules.ME32().validate(related)


# -- Ceiling/quota definition existence


def test_ME10():
    """
    The order number must be specified if the "order number flag" (specified in
    the measure type record) has the value "mandatory".

    If the flag is set to "not permitted" then the field cannot be entered.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME10().validate(
            factories.MeasureFactory.create(
                measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
                order_number=None,
                dead_order_number=None,
            ),
        )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME10().validate(
            factories.MeasureFactory.create(
                measure_type__order_number_capture_code=OrderNumberCaptureCode.NOT_PERMITTED,
                order_number=factories.QuotaOrderNumberFactory.create(),
            ),
        )


@only_applicable_after("2007-12-31")
def test_ME116(date_ranges):
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME116().validate(
            factories.MeasureWithQuotaFactory.create(
                order_number__valid_between=date_ranges.starts_with_normal,
                valid_between=date_ranges.normal,
            ),
        )


@only_applicable_after("2007-12-31")
def test_ME117():
    """
    When a measure has a quota measure type then the origin must exist as a
    quota order number origin.

    This rule is only applicable for measures with start date after 31/12/2007.

    Only origins for quota order numbers managed by the first come first served
    principle are in scope
    """

    origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number__mechanism=AdministrationMechanism.FCFS,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME117().validate(
            factories.MeasureWithQuotaFactory.create(
                order_number=origin.order_number,
                geographical_area=factories.GeographicalAreaFactory.create(),
            ),
        )

    business_rules.ME117().validate(
        factories.MeasureWithQuotaFactory.create(
            order_number=origin.order_number,
            geographical_area=origin.geographical_area,
        ),
    )


@pytest.mark.skip(reason="Duplicate of ME116")
def test_ME118():
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    assert False


@pytest.mark.xfail(reason="need to confirm rule is needed")
@only_applicable_after("2007-12-31")
def test_ME119(date_ranges):
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number origin must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME119().validate(
            factories.MeasureWithQuotaFactory.create(
                order_number__origin__valid_between=date_ranges.starts_with_normal,
                valid_between=date_ranges.normal,
            ),
        )


# -- Relation with additional codes


@pytest.mark.parametrize(
    "additional_code, goods_nomenclature, expect_error",
    [
        (None, None, True),
        (None, True, False),
        (True, None, False),
        (True, True, False),
    ],
)
def test_ME9(additional_code, goods_nomenclature, expect_error):
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

    if additional_code:
        additional_code = factories.AdditionalCodeFactory.create()

    if goods_nomenclature:
        goods_nomenclature = factories.GoodsNomenclatureFactory.create()

    try:
        business_rules.ME9().validate(
            factories.MeasureFactory.create(
                additional_code=additional_code,
                goods_nomenclature=goods_nomenclature,
            ),
        )
    except BusinessRuleViolation:
        if not expect_error:
            raise
    else:
        if expect_error:
            pytest.fail(reason="DID NOT RAISE BusinessRuleViolation")


def test_ME12():
    """If the additional code is specified then the additional code type must
    have a relationship with the measure type."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME12().validate(
            factories.MeasureFactory.create(
                additional_code=factories.AdditionalCodeFactory.create(),
            ),
        )

    rel = factories.AdditionalCodeTypeMeasureTypeFactory.create()

    business_rules.ME12().validate(
        factories.MeasureFactory.create(
            measure_type=rel.measure_type,
            additional_code__type=rel.additional_code_type,
            goods_nomenclature__item_id="7700000000",
        ),
    )


@requires_meursing_tables
def test_ME13():
    """If the additional code type is related to a Meursing table plan then only
    the additional code can be specified: no goods code, order number or
    reduction indicator."""
    assert False


@requires_meursing_tables
def test_ME14():
    """If the additional code type is related to a Meursing table plan then the
    additional code must exist as a Meursing additional code."""
    assert False


@requires_meursing_tables
def test_ME15():
    """If the additional code type is related to a Meursing table plan then the
    validity period of the additional code must span the validity period of the
    measure."""
    assert False


def test_ME17(reference_nonexistent_record):
    """
    If the additional code type has as application "non-Meursing" then the
    additional code must exist as a non-Meursing additional code.

    UK tariff does not use meursing tables, so this is essentially saying that
    an additional code must exist.
    """

    with reference_nonexistent_record(
        factories.MeasureWithAdditionalCodeFactory,
        "additional_code",
    ) as measure:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME17().validate(measure)


@pytest.mark.skip(reason="No meursing, so duplicate of ME115")
def test_ME18():
    """If the additional code type has as application "non-Meursing" then the
    validity period of the non-Meursing additional code must span the validity
    period of the measure."""


# -- Export Refund nomenclature measures


@requires_export_refund_nomenclature
def test_ME19():
    """If the additional code type has as application "ERN" then the goods code
    must be specified but the order number is blocked for input."""
    assert False


@requires_export_refund_nomenclature
def test_ME21():
    """If the additional code type has as application "ERN" then the combination
    of goods code + additional code must exist as an ERN product code and its
    validity period must span the validity period of the measure."""
    assert False


# -- Export Refund for Processed Agricultural Goods measures


@requires_export_refund_nomenclature
def test_ME112():
    """If the additional code type has as application "Export Refund for
    Processed Agricultural Goods" then the measure does not require a goods
    code."""
    assert False


@requires_export_refund_nomenclature
def test_ME113():
    """If the additional code type has as application "Export Refund for
    Processed Agricultural Goods" then the additional code must exist as an
    Export Refund for Processed Agricultural Goods additional code."""
    assert False


@requires_export_refund_nomenclature
def test_ME114():
    """If the additional code type has as application "Export Refund for
    Processed Agricultural Goods" then the validity period of the Export Refund
    for Processed Agricultural Goods additional code must span the validity
    period of the measure."""
    assert False


# -- Relation with regulations


def test_ME24(reference_nonexistent_record):
    """
    The role + regulation id must exist.

    If no measure start date is specified it defaults to the regulation start
    date.
    """

    with reference_nonexistent_record(
        factories.MeasureFactory,
        "generating_regulation",
    ) as measure:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME24().validate(measure)


@pytest.mark.skip(reason="All UK tariff regulations are Base regulations")
def test_ME86():
    """The role of the entered regulation must be a Base, a Modification, a Provisional
    Anti- Dumping, a Definitive Anti-Dumping.
    """
    assert False


def test_ME87(date_ranges):
    """
    The validity period of the measure (implicit or explicit) must reside within
    the effective validity period of its supporting regulation. The effective
    validity period is the validity period of the regulation taking into account
    extensions and abrogation.

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
    with pytest.raises(BusinessRuleViolation):
        business_rules.ME87().validate(
            factories.MeasureFactory.create(
                generating_regulation__valid_between=date_ranges.starts_with_normal,
                valid_between=date_ranges.normal,
            ),
        )

    # implicit - regulation end date supercedes measure end date
    # generating reg:  s---x
    # measure:         s---i----x       i = implicit end date
    with pytest.raises(BusinessRuleViolation):
        business_rules.ME87().validate(
            factories.MeasureFactory.create(
                generating_regulation__valid_between=date_ranges.starts_with_normal,
                valid_between=date_ranges.normal,
            ),
        )


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used",
)
def test_ME26():
    """The entered regulation may not be completely abrogated."""


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used",
)
def test_ME27():
    """The entered regulation may not be fully replaced."""


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used",
)
def test_ME28():
    """The entered regulation may not be partially replaced for the measure
    type, geographical area or chapter (first two digits of the goods code) of
    the measure."""


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used",
)
def test_ME29():
    """If the entered regulation is a modification regulation then its base
    regulation may not be completely abrogated."""


def test_ME33(date_ranges):
    """
    A justification regulation may not be entered if the measure end date is not
    filled in.

    A justification regulation is used to ‘justify’ terminating a regulation.
    There is no requirement for this in UK law, nor for audit purposes in the UK
    tariff, however it is a mandatory field in the database and in CDS. The rule
    is self-explanatory: if there no end date on the measure, then the
    justification regulation field must be set to null.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME33().validate(
            factories.MeasureFactory.create(
                valid_between=date_ranges.no_end,
                terminating_regulation=factories.RegulationFactory.create(),
            ),
        )


def test_ME34(date_ranges):
    """
    A justification regulation must be entered if the measure end date is filled
    in.

    The justification regulation fields MUST be completed when the regulation is end-dated.
    - Users should be discouraged from end dating regulations, instead they should end
      date measures.
    - Always use the measure generating regulation ID and role to populate the
      justification equivalents, if the end date needs to be entered on a regulation.
    """

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME34().validate(
            factories.MeasureFactory.create(
                valid_between=date_ranges.normal,
                terminating_regulation=None,
            ),
        )


# -- Measure component


@pytest.mark.parametrize(
    "applicability_code, component, condition_component",
    [
        (ApplicabilityCode.MANDATORY, False, False),
        (ApplicabilityCode.NOT_PERMITTED, True, False),
        (ApplicabilityCode.NOT_PERMITTED, False, True),
        (ApplicabilityCode.MANDATORY, True, True),
    ],
)
def test_ME40(applicability_code, component, condition_component):
    """
    If the flag "duty expression" on measure type is "mandatory" then at least
    one measure component or measure condition component record must be
    specified.  If the flag is set "not permitted" then no measure component or
    measure condition component must exist.  Measure components and measure
    condition components are mutually exclusive. A measure can have either
    components or condition components (if the ‘duty expression’ flag is
    ‘mandatory’ or ‘optional’) but not both.

    This describes the fact that measures of certain types MUST have components
    (duties) assigned to them, whereas others must not. Note the sub-clause also
    – if the value of the field “Component applicable” is set to 1 (mandatory)
    on a measure type, then when the measure is created, there must be either
    measure components or measure condition components assigned to the measure,
    but not both. CDS will generate errors if either of these conditions are not
    met.
    """

    measure = factories.MeasureFactory.create(
        measure_type__measure_component_applicability_code=applicability_code,
    )

    if component:
        factories.MeasureComponentFactory.create(component_measure=measure)

    if condition_component:
        factories.MeasureConditionComponentFactory.create(
            condition__dependent_measure=measure,
        )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME40().validate(measure)


def test_ME41(reference_nonexistent_record):
    """The referenced duty expression must exist."""

    with reference_nonexistent_record(
        factories.MeasureComponentFactory,
        "duty_expression",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME41().validate(component)


def test_ME42(date_ranges):
    """The validity period of the duty expression must span the validity period
    of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME42().validate(
            factories.MeasureComponentFactory.create(
                duty_expression__valid_between=date_ranges.normal,
                component_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME43():
    """
    The same duty expression can only be used once with the same measure.

    Even if an expression that (in English) reads the same needs to be used more
    than once in a measure, we must use a different expression ID, never the
    same one twice.
    """

    measure = factories.MeasureFactory.create()
    existing = factories.MeasureComponentFactory.create(component_measure=measure)
    component = factories.MeasureComponentFactory.create(
        duty_expression=existing.duty_expression,
        component_measure=measure,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.ME43().validate(component)


@pytest.mark.parametrize(
    "applicability_code, amount",
    [
        (ApplicabilityCode.MANDATORY, None),
        (ApplicabilityCode.NOT_PERMITTED, Decimal(1)),
    ],
)
def test_ME45(applicability_code, amount):
    """
    If the flag "amount" on duty expression is "mandatory" then an amount must
    be specified.

    If the flag is set "not permitted" then no amount may be entered.
    """

    measure = factories.MeasureFactory.create()
    factories.MeasureComponentFactory.create(
        component_measure=measure,
        duty_expression__duty_amount_applicability_code=applicability_code,
        duty_amount=amount,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME45().validate(measure)


@pytest.mark.parametrize(
    "applicability_code, monetary_unit",
    [
        (ApplicabilityCode.MANDATORY, None),
        (ApplicabilityCode.NOT_PERMITTED, True),
    ],
)
def test_ME46(applicability_code, monetary_unit):
    """
    If the flag "monetary unit" on duty expression is "mandatory" then a
    monetary unit must be specified.

    If the flag is set "not permitted" then no monetary unit may be entered.
    """

    if monetary_unit:
        monetary_unit = factories.MonetaryUnitFactory.create()

    measure = factories.MeasureFactory.create()
    factories.MeasureComponentFactory.create(
        component_measure=measure,
        duty_expression__monetary_unit_applicability_code=applicability_code,
        monetary_unit=monetary_unit,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME46().validate(measure)


@pytest.mark.parametrize(
    "applicability_code, measurement",
    [
        (ApplicabilityCode.MANDATORY, None),
        (ApplicabilityCode.NOT_PERMITTED, True),
    ],
)
def test_ME47(applicability_code, measurement):
    """
    If the flag "measurement unit" on duty expression is "mandatory" then a
    measurement unit must be specified.

    If the flag is set "not permitted" then no measurement unit may be entered.
    """

    if measurement:
        measurement = factories.MeasurementFactory.create()

    measure = factories.MeasureFactory.create()
    factories.MeasureComponentWithMeasurementFactory.create(
        component_measure=measure,
        duty_expression__measurement_unit_applicability_code=applicability_code,
        component_measurement=measurement,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME47().validate(measure)


def test_ME48(reference_nonexistent_record):
    """The referenced monetary unit must exist."""

    with reference_nonexistent_record(
        factories.MeasureComponentWithMonetaryUnitFactory,
        "monetary_unit",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME48().validate(component)


def test_ME49(date_ranges):
    """The validity period of the referenced monetary unit must span the
    validity period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME49().validate(
            factories.MeasureComponentWithMonetaryUnitFactory.create(
                monetary_unit__valid_between=date_ranges.normal,
                component_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME50(reference_nonexistent_record):
    """The combination measurement unit + measurement unit qualifier must
    exist."""

    with reference_nonexistent_record(
        factories.MeasureComponentWithMeasurementFactory,
        "component_measurement",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME50().validate(component)


def test_ME51(date_ranges):
    """The validity period of the measurement unit must span the validity period
    of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME51().validate(
            factories.MeasureComponentWithMeasurementFactory.create(
                component_measurement__measurement_unit__valid_between=date_ranges.normal,
                component_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME52(date_ranges):
    """The validity period of the measurement unit qualifier must span the
    validity period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME52().validate(
            factories.MeasureComponentWithMeasurementFactory.create(
                component_measurement__measurement_unit_qualifier__valid_between=date_ranges.normal,
                component_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


# -- Measure condition and Measure condition component


def test_ME53(reference_nonexistent_record):
    """The referenced measure condition must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionComponentFactory,
        "condition",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME53().validate(component)


@pytest.mark.skip(reason="Erroneous business rule")
def test_ME54():
    """
    The validity period of the referenced measure condition must span the
    validity period of the measure.

    Not required - disregard: as far as we can see, this is an erroneous business rule.
    The measure condition table does not have a start and end date field. The condition
    adopts the start and end dates of the parent measure. Similarly, there are no start
    and end dates associated with a measure condition component (or for that matter a
    measure component).  They all adopt the date constraints of the parent measure.
    """


@pytest.mark.skip(reason="Erroneous business rule")
def test_ME55():
    """
    A measure condition refers to a measure condition or to a condition +
    certificate or to a condition + amount specifications.

    Disregard: this has been written so vaguely that there are no rules to be gleaned
    from it.
    """


def test_ME56(reference_nonexistent_record):
    """The referenced certificate must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionWithCertificateFactory,
        "required_certificate",
    ) as condition:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME56().validate(condition)


def test_ME57(date_ranges):
    """The validity period of the referenced certificate must span the validity
    period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME57().validate(
            factories.MeasureConditionWithCertificateFactory.create(
                required_certificate__valid_between=date_ranges.normal,
                dependent_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME58():
    """The same certificate can only be referenced once by the same measure and
    the same condition type."""

    existing = factories.MeasureConditionFactory.create(
        required_certificate=factories.CertificateFactory.create(),
    )
    factories.MeasureConditionFactory.create(
        condition_code=existing.condition_code,
        dependent_measure=existing.dependent_measure,
        required_certificate=existing.required_certificate,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME58().validate(existing)


def test_ME59(reference_nonexistent_record):
    """The referenced action code must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionFactory,
        "action",
    ) as condition:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME59().validate(condition)


def test_ME60(reference_nonexistent_record):
    """The referenced monetary unit must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionFactory,
        "monetary_unit",
    ) as condition:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME60().validate(condition)


def test_ME61(date_ranges):
    """The validity period of the referenced monetary unit must span the
    validity period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME61().validate(
            factories.MeasureConditionFactory.create(
                monetary_unit__valid_between=date_ranges.normal,
                dependent_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME62(reference_nonexistent_record):
    """The combination measurement unit + measurement unit qualifier must
    exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionWithMeasurementFactory,
        "condition_measurement",
    ) as condition:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME62().validate(condition)


def test_ME63(date_ranges):
    """The validity period of the measurement unit must span the validity period
    of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME63().validate(
            factories.MeasureConditionWithMeasurementFactory.create(
                condition_measurement__measurement_unit__valid_between=date_ranges.normal,
                dependent_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME64(date_ranges):
    """The validity period of the measurement unit qualifier must span the
    validity period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME64().validate(
            factories.MeasureConditionWithMeasurementFactory.create(
                condition_measurement__measurement_unit_qualifier__valid_between=date_ranges.normal,
                dependent_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


def test_ME105(reference_nonexistent_record):
    """The referenced duty expression must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionComponentFactory,
        "duty_expression",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME105().validate(component)


def test_ME106(date_ranges):
    """The validity period of the duty expression must span the validity period
    of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME106().validate(
            factories.MeasureConditionComponentFactory.create(
                duty_expression__valid_between=date_ranges.starts_with_normal,
                condition__dependent_measure__valid_between=date_ranges.normal,
            ),
        )


@pytest.mark.parametrize(
    "expression, same_condition, expect_error",
    [
        (DutyExpressionId.DE1, False, False),
        (DutyExpressionId.DE2, True, False),
        (DutyExpressionId.DE1, True, True),
    ],
)
def test_ME108(expression, same_condition, expect_error):
    """
    The same duty expression can only be used once within condition components
    of the same condition of the same measure.

    (i.e. it can be re-used in other conditions, no matter what condition type,
    of the same measure)
    """

    measure = factories.MeasureFactory.create()
    condition = factories.MeasureConditionFactory.create(dependent_measure=measure)
    factories.MeasureConditionComponentFactory.create(
        duty_expression__sid=DutyExpressionId.DE1,
        condition=condition,
    )

    if not same_condition:
        condition = factories.MeasureConditionFactory.create(dependent_measure=measure)

    component = factories.MeasureConditionComponentFactory.create(
        duty_expression__sid=expression,
        condition=condition,
    )

    try:
        business_rules.ME108().validate(component)
    except BusinessRuleViolation:
        if not expect_error:
            raise
    else:
        if expect_error:
            pytest.fail(reason="DID NOT RAISE BusinessRuleViolation")


@pytest.mark.parametrize(
    "applicability_code, amount",
    [
        (ApplicabilityCode.MANDATORY, None),
        (ApplicabilityCode.NOT_PERMITTED, Decimal(1)),
    ],
)
def test_ME109(applicability_code, amount):
    """
    If the flag 'amount' on duty expression is 'mandatory' then an amount must
    be specified.

    If the flag is set to 'not permitted' then no amount may be entered.
    """

    measure = factories.MeasureFactory.create()
    factories.MeasureConditionComponentFactory.create(
        condition__dependent_measure=measure,
        duty_expression__duty_amount_applicability_code=applicability_code,
        duty_amount=amount,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME109().validate(measure)


@pytest.mark.parametrize(
    "applicability_code, monetary_unit",
    [
        (ApplicabilityCode.MANDATORY, None),
        (ApplicabilityCode.NOT_PERMITTED, True),
    ],
)
def test_ME110(applicability_code, monetary_unit):
    """
    If the flag 'monetary unit' on duty expression is 'mandatory' then a
    monetary unit must be specified.

    If the flag is set to 'not permitted' then no monetary unit may be entered.
    """

    if monetary_unit:
        monetary_unit = factories.MonetaryUnitFactory.create()

    measure = factories.MeasureFactory.create()
    factories.MeasureConditionComponentFactory.create(
        condition__dependent_measure=measure,
        duty_expression__monetary_unit_applicability_code=applicability_code,
        monetary_unit=monetary_unit,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME110().validate(measure)


@pytest.mark.parametrize(
    "applicability_code, measurement",
    [
        (ApplicabilityCode.MANDATORY, None),
        (ApplicabilityCode.NOT_PERMITTED, True),
    ],
)
def test_ME111(applicability_code, measurement):
    """
    If the flag 'measurement unit' on duty expression is 'mandatory' then a
    measurement unit must be specified.

    If the flag is set to 'not permitted' then no measurement unit may be
    entered.
    """

    if measurement:
        measurement = factories.MeasurementFactory.create()

    measure = factories.MeasureFactory.create()
    factories.MeasureConditionComponentWithMeasurementFactory.create(
        condition__dependent_measure=measure,
        duty_expression__measurement_unit_applicability_code=applicability_code,
        condition_component_measurement=measurement,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME111().validate(measure)


# -- Measure excluded geographical area


def test_ME65():
    """An exclusion can only be entered if the measure is applicable to a geographical
    area group (area code = 1)."""

    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        modified_measure__geographical_area__area_code=AreaCode.COUNTRY,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME65().validate(exclusion)


def test_ME66():
    """The excluded geographical area must be a member of the geographical area
    group."""

    membership = factories.GeographicalMembershipFactory.create()
    measure = factories.MeasureFactory.create(geographical_area=membership.geo_group)

    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        modified_measure=measure,
        excluded_geographical_area=membership.member,
    )

    business_rules.ME66().validate(exclusion)

    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        modified_measure=measure,
        excluded_geographical_area=factories.GeographicalAreaFactory.create(),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME66().validate(exclusion)


@pytest.mark.xfail(reason="ME67 disabled")
def test_ME67(date_ranges):
    """The membership period of the excluded geographical area must span the
    validity period of the measure."""

    membership = factories.GeographicalMembershipFactory.create(
        valid_between=date_ranges.normal,
    )
    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership.member,
        modified_measure__geographical_area=membership.geo_group,
        modified_measure__valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.ME67().validate(exclusion.modified_measure)


def test_ME68():
    """The same geographical area can only be excluded once by the same
    measure."""

    existing = factories.MeasureExcludedGeographicalAreaFactory.create()

    factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=existing.excluded_geographical_area,
        modified_measure=existing.modified_measure,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME68().validate(existing)


# -- Footnote association


def test_ME69(reference_nonexistent_record):
    """The associated footnote must exist."""

    with reference_nonexistent_record(
        factories.FootnoteAssociationMeasureFactory,
        "associated_footnote",
    ) as assoc:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME69().validate(assoc)


def test_ME70():
    """The same footnote can only be associated once with the same measure."""

    existing = factories.FootnoteAssociationMeasureFactory.create()
    factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=existing.footnoted_measure,
        associated_footnote=existing.associated_footnote,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME70().validate(existing)


def test_ME71():
    """Footnotes with a footnote type for which the application type = "CN footnotes"
    cannot be associated with TARIC codes (codes with pos. 9-10 different from 00)"""

    assoc = factories.FootnoteAssociationMeasureFactory.create(
        associated_footnote__footnote_type__application_code=ApplicationCode.CN_MEASURES,
        footnoted_measure__goods_nomenclature__item_id="0123456789",
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME71().validate(assoc)


@pytest.mark.skip(reason="No way to test violation")
def test_ME72():
    """Footnotes with a footnote type for which the application type = "measure
    footnotes" can be associated at any level.

    This refers to footnotes of type PB, IS, CD, MX, TM, EU, CG, TR, CO, OZ, MG, which
    have an application code of “7”.
    """

    assert False


def test_ME73(date_ranges):
    """The validity period of the associated footnote must span the validity
    period of the measure."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME73().validate(
            factories.FootnoteAssociationMeasureFactory.create(
                associated_footnote__valid_between=date_ranges.normal,
                footnoted_measure__valid_between=date_ranges.overlap_normal,
            ),
        )


# -- Partial temporary stop
@requires_partial_temporary_stop
def test_ME39():
    """The validity period of the measure must span the validity period of all
    related partial temporary stop (PTS) records."""
    assert False


@requires_partial_temporary_stop
def test_ME74():
    """The start date of the PTS must be less than or equal to the end date."""
    assert False


@requires_partial_temporary_stop
def test_ME75():
    """The PTS regulation and abrogation regulation must be the same if the
    start date and the end date are entered when creating the record."""
    assert False


@requires_partial_temporary_stop
def test_ME76():
    """The abrogation regulation may not be entered if the PTS end date is not
    filled in."""
    assert False


@requires_partial_temporary_stop
def test_ME77():
    """The abrogation regulation must be entered if the PTS end date is filled
    in."""
    assert False


@requires_partial_temporary_stop
def test_ME78():
    """The abrogation regulation must be different from the PTS regulation if
    the end date is filled in during a modification."""
    assert False


@requires_partial_temporary_stop
def test_ME79():
    """There may be no overlap between different PTS periods."""
    assert False


# -- Justification regulation


@pytest.mark.xfail(reason="confirm rule is needed")
def test_ME104(date_ranges, unapproved_transaction):
    """
    The justification regulation must be either:

        - the measure’s measure-generating regulation, or
        - a measure-generating regulation, valid on the day after the measure’s
          (explicit) end date.
    If the measure’s measure-generating regulation is ‘approved’, then so must be the
    justification regulation.
    """

    measure = factories.MeasureFactory.create(
        valid_between=date_ranges.normal,
        transaction=unapproved_transaction,
    )
    generating = measure.generating_regulation
    terminating = measure.terminating_regulation

    assert (
        terminating.regulation_id == generating.regulation_id
        and terminating.role_type == generating.role_type
    )

    measure.terminating_regulation = factories.RegulationFactory.create(
        valid_between=TaricDateRange(
            measure.valid_between.upper + relativedelta(days=+1),
            None,
        ),
    )
    business_rules.ME104().validate(measure)

    measure.terminating_regulation = factories.RegulationFactory.create()
    with pytest.raises(BusinessRuleViolation):
        business_rules.ME104().validate(measure)


def test_measurement_unit_qualifier_is_optional():
    """In TARIC measurement unit qualifiers do not have to be used on every
    measure."""
    factories.MeasurementFactory.create(measurement_unit_qualifier=None)
