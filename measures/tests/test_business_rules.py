from decimal import Decimal

import factory
import pytest
from dateutil.relativedelta import relativedelta
from django.db import DataError
from django.db.models import signals

from common.business_rules import BusinessRuleViolation
from common.business_rules import UniqueIdentifyingFields
from common.tests import factories
from common.tests.factories import date_ranges
from common.tests.factories import end_date
from common.tests.util import Dates
from common.tests.util import only_applicable_after
from common.tests.util import raises_if
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


def test_MTS1(assert_handles_duplicates):
    """The measure type series must be unique."""
    assert_handles_duplicates(
        factories.MeasureTypeSeriesFactory,
        business_rules.MTS1,
    )


def test_MTS2(delete_record):
    """The measure type series cannot be deleted if it is associated with a
    measure type."""

    measure_type = factories.MeasureTypeFactory.create()
    deleted = delete_record(measure_type.measure_type_series)

    with pytest.raises(BusinessRuleViolation):
        business_rules.MTS2(deleted.transaction).validate(deleted)


def test_MTS3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureTypeSeriesFactory.create(valid_between=date_ranges.backwards)


# 235 - MEASURE TYPE


def test_MT1(assert_handles_duplicates):
    """The measure type code must be unique."""
    assert_handles_duplicates(
        factories.MeasureTypeFactory,
        business_rules.MT1,
    )


def test_MT2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureTypeFactory.create(valid_between=date_ranges.backwards)


def test_MT3(assert_spanning_enforced):
    """When a measure type is used in a measure then the validity period of the
    measure type must span the validity period of the measure."""
    assert_spanning_enforced(
        factories.MeasureTypeFactory,
        business_rules.MT3,
        measure=factories.related_factory(
            factories.MeasureFactory,
            factory_related_name="measure_type",
        ),
    )


def test_MT4(reference_nonexistent_record):
    """The referenced measure type series must exist."""

    with reference_nonexistent_record(
        factories.MeasureTypeFactory,
        "measure_type_series",
    ) as measure_type:
        with pytest.raises(BusinessRuleViolation):
            business_rules.MT4(measure_type.transaction).validate(measure_type)


def test_MT7(delete_record):
    """A measure type can not be deleted if it is used in a measure."""

    measure = factories.MeasureFactory.create()
    deleted = delete_record(measure.measure_type)
    with pytest.raises(BusinessRuleViolation):
        business_rules.MT7(deleted.transaction).validate(deleted)


def test_MT10(assert_spanning_enforced):
    """The validity period of the measure type series must span the validity
    period of the measure type."""

    assert_spanning_enforced(
        factories.MeasureTypeFactory,
        business_rules.MT10,
    )


# 350 - MEASURE CONDITION CODE


def test_MC1(assert_handles_duplicates):
    """The code of the measure condition code must be unique."""
    assert_handles_duplicates(
        factories.MeasureConditionCodeFactory,
        business_rules.MC1,
    )


def test_MC2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureConditionCodeFactory.create(
            valid_between=date_ranges.backwards,
        )


def test_MC3(assert_spanning_enforced):
    """If a measure condition code is used in a measure then the validity period
    of the measure condition code must span the validity period of the
    measure."""
    assert_spanning_enforced(
        factories.MeasureConditionFactory,
        business_rules.MC3,
    )


def test_MC4(delete_record):
    """The measure condition code cannot be deleted if it is used in a measure
    condition component."""

    component = factories.MeasureConditionComponentFactory.create()
    deleted = delete_record(component.condition.condition_code)
    with pytest.raises(BusinessRuleViolation):
        business_rules.MC4(deleted.transaction).validate(deleted)


# 355 - MEASURE ACTION


def test_MA1(assert_handles_duplicates):
    """The code of the measure action must be unique."""
    assert_handles_duplicates(
        factories.MeasureActionFactory,
        business_rules.MA1,
    )


def test_MA2(delete_record):
    """The measure action can not be deleted if it is used in a measure
    condition component."""

    component = factories.MeasureConditionComponentFactory.create()
    deleted = delete_record(component.condition.action)

    with pytest.raises(BusinessRuleViolation):
        business_rules.MA2(deleted.transaction).validate(deleted)


def test_MA3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.MeasureActionFactory.create(valid_between=date_ranges.backwards)


def test_MA4(assert_spanning_enforced):
    """If a measure action is used in a measure then the validity period of the
    measure action must span the validity period of the measure."""
    assert_spanning_enforced(
        factories.MeasureConditionFactory,
        business_rules.MA4,
    )


# 430 - MEASURE


def test_ME1(assert_handles_duplicates):
    """
    The combination of measure type + geographical area + goods nomenclature
    item id.

    + additional code type + additional code + order number + reduction
    indicator + start date must be unique.
    """
    assert_handles_duplicates(
        factories.MeasureFactory,
        business_rules.ME1,
        identifying_fields=(
            "measure_type",
            "geographical_area",
            "goods_nomenclature",
            "additional_code",
            "order_number",
            "reduction",
            "valid_between__lower",
        ),
    )


def test_ME2(reference_nonexistent_record):
    """The measure type must exist."""

    with reference_nonexistent_record(
        factories.MeasureFactory,
        "measure_type",
    ) as measure:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME2(measure.transaction).validate(measure)


def test_ME3(assert_spanning_enforced):
    """The validity period of the measure type must span the validity period of
    the measure."""
    assert_spanning_enforced(
        factories.MeasureFactory,
        business_rules.ME3,
    )


def test_ME4(reference_nonexistent_record):
    """The geographical area must exist."""

    with reference_nonexistent_record(
        factories.MeasureFactory,
        "geographical_area",
    ) as measure:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME4(measure.transaction).validate(measure)


def test_ME5(assert_spanning_enforced):
    """The validity period of the geographical area must span the validity
    period of the measure."""
    assert_spanning_enforced(
        factories.MeasureFactory,
        business_rules.ME5,
    )


def test_ME6(reference_nonexistent_record):
    """The goods code must exist."""

    def teardown(good):
        for indent in good.indents.all():
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
            business_rules.ME6(measure.transaction).validate(measure)


def test_ME7():
    """The goods nomenclature code must be a product code; that is, it may not
    be an intermediate line."""
    measure = factories.MeasureFactory.create(goods_nomenclature__suffix="00")
    with pytest.raises(BusinessRuleViolation):
        business_rules.ME7(measure.transaction).validate(measure)

    measure = factories.MeasureFactory.create(goods_nomenclature__suffix="80")

    business_rules.ME7(measure.transaction).validate(measure)


def test_ME8(assert_spanning_enforced):
    """The validity period of the goods code must span the validity period of
    the measure."""
    assert_spanning_enforced(
        factories.MeasureFactory,
        business_rules.ME8,
    )


def test_ME88():
    """The level of the goods code, if present, cannot exceed the explosion
    level of the measure type."""

    good = factories.GoodsNomenclatureFactory.create(item_id="9999999900")
    measure = factories.MeasureFactory.create(
        measure_type__measure_explosion_level=2,
        goods_nomenclature=good,
        leave_measure=True,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME88(measure.transaction).validate(measure)


@pytest.mark.parametrize(
    ("existing_code", "overlapping_code", "error_expected"),
    (
        (False, True, True),
        (True, False, True),
        (True, True, False),
        (False, False, False),
    ),
)
def test_ME16(existing_code, overlapping_code, error_expected):
    """Integrating a measure with an additional code when an equivalent or
    overlapping measures without additional code already exists and vice-versa,
    should be forbidden."""

    additional_code = factories.AdditionalCodeFactory.create()
    existing = factories.MeasureFactory.create(
        additional_code=(additional_code if existing_code else None),
    )
    measure = factories.MeasureFactory.create(
        measure_type=existing.measure_type,
        geographical_area=existing.geographical_area,
        goods_nomenclature=existing.goods_nomenclature,
        additional_code=(additional_code if overlapping_code else None),
        order_number=existing.order_number,
        reduction=existing.reduction,
    )
    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME16(measure.transaction).validate(measure)


def test_ME115(assert_spanning_enforced):
    """The validity period of the referenced additional code must span the
    validity period of the measure."""
    assert_spanning_enforced(
        factories.MeasureWithAdditionalCodeFactory,
        business_rules.ME115,
    )


@pytest.mark.parametrize(
    ("measure_dates", "regulation_dates", "regulation_effective_end", "error_expected"),
    (
        ("normal", "no_end", "no_end", False),
        ("no_end", "no_end", "no_end", False),
        ("no_end", "normal", "no_end", False),
        ("no_end", "no_end", "normal", False),
        ("no_end", "no_end", "earlier", True),
        ("no_end", "earlier", "no_end", True),
    ),
)
def test_ME25(
    measure_dates,
    regulation_dates,
    regulation_effective_end,
    error_expected,
):
    """
    If the measure’s end date is specified (implicitly or explicitly) then the
    start date of the measure must be less than or equal to the end date.

    End date will in almost all circumstances be explicit for measures. If it is
    not, the implicit end date will come from the regulation. It is possible for
    the regulation to have an end date and an optional "effective end date". If
    the effective end date is present it should override the original end date.
    """
    measure = factories.MeasureFactory.create(
        valid_between=date_ranges(measure_dates),
        generating_regulation__valid_between=date_ranges(regulation_dates),
        generating_regulation__effective_end_date=end_date(regulation_effective_end),
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME25(measure.transaction).validate(measure)


@pytest.fixture
def existing_goods_nomenclature(date_ranges):
    return factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.big,
    )


def updated_goods_nomenclature(e):
    original = e.indents.get()
    original.indent = 1
    original.save(force_write=True)

    good = factories.GoodsNomenclatureFactory.create(
        item_id=e.item_id[:8] + "90",
        valid_between=e.valid_between,
        indent__indent=e.indents.first().indent + 1,
    )

    factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=good,
        update_type=UpdateType.UPDATE,
        version_group=good.indents.first().version_group,
        validity_start=good.indents.first().validity_start,
        indent=e.indents.first().indent - 1,
    )

    return good


@pytest.fixture(
    params=(
        (lambda e: e, True),
        (
            lambda e: factories.GoodsNomenclatureFactory.create(
                item_id=e.item_id[:8] + "90",
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
        (None, {"valid_between": factories.date_ranges("normal")}, True),
        (
            None,
            {
                "valid_between": factories.date_ranges("no_end"),
                "generating_regulation__valid_between": factories.date_ranges("normal"),
                "generating_regulation__effective_end_date": factories.end_date(
                    "normal",
                ),
            },
            True,
        ),
        (
            {"valid_between": factories.date_ranges("no_end")},
            {"update_type": UpdateType.DELETE},
            False,
        ),
    ),
    ids=[
        "explicit",
        "implicit",
        "draft:previously",
    ],
)
def existing_measure(request, existing_goods_nomenclature):
    """
    Returns a measure that with an attached quota and a flag indicating whether
    the date range of the measure overlaps with the "normal" date range.

    The measure will either be a new measure or a draft UPDATE to an existing
    measure. If it is an UPDATE, the measure will be in an unapproved
    workbasket.
    """
    data = {
        "goods_nomenclature": existing_goods_nomenclature,
        "additional_code": factories.AdditionalCodeFactory.create(),
    }

    previous, now, overlaps_normal = request.param
    if previous:
        old_version = factories.MeasureWithQuotaFactory.create(**data, **previous)
        return (
            factories.MeasureWithQuotaFactory.create(
                version_group=old_version.version_group,
                transaction=factories.UnapprovedTransactionFactory(),
                **data,
                **now,
            ),
            overlaps_normal,
        )
    else:
        return factories.MeasureWithQuotaFactory.create(**data, **now), overlaps_normal


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
                "valid_between": d.overlap_normal_earlier,
                "measure_type": factories.MeasureTypeFactory.create(),
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "geographical_area": factories.GeographicalAreaFactory.create(),
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "order_number": factories.QuotaOrderNumberFactory.create(),
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "additional_code": factories.AdditionalCodeFactory.create(),
            },
            False,
        ),
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "reduction": None,
            },
            False,
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
        (
            lambda d: {
                "valid_between": d.overlap_normal_earlier,
                "update_type": UpdateType.DELETE,
            },
            False,
        ),
    ),
    ids=[
        "explicit:overlapping",
        "explicit:overlapping:measure_type",
        "explicit:overlapping:geographical_area",
        "explicit:overlapping:order_number",
        "explicit:overlapping:additional_code",
        "explicit:overlapping:reduction",
        "implicit:not-overlapping",
        "explicit:not-overlapping",
        "deleted",
    ],
)
def related_measure_dates(request, date_ranges):
    callable, date_overlap = request.param
    return callable(date_ranges), date_overlap


@pytest.fixture
def related_measure_data(
    related_measure_dates,
    related_goods_nomenclature,
    existing_measure,
):
    nomenclature, nomenclature_overlap = related_goods_nomenclature
    validity_data, date_overlap = related_measure_dates
    existing_measure, overlaps_normal = existing_measure
    full_data = {
        "goods_nomenclature": nomenclature,
        "measure_type": existing_measure.measure_type,
        "geographical_area": existing_measure.geographical_area,
        "order_number": existing_measure.order_number,
        "additional_code": existing_measure.additional_code,
        "reduction": existing_measure.reduction,
        "transaction": existing_measure.transaction.workbasket.new_transaction(),
        **validity_data,
    }
    error_expected = date_overlap and nomenclature_overlap and overlaps_normal

    return full_data, error_expected


def test_ME32(related_measure_data):
    """
    There may be no overlap in time with other measure occurrences with a goods
    code in the same nomenclature hierarchy which references the same measure
    type, geo area, order number, additional code and reduction indicator. This
    rule is not applicable for Meursing additional codes.

    This is an extension of the previously described ME1 to all commodity codes
    in the upward hierarchy and all commodity codes in the downward hierarchy.
    """

    related_data, error_expected = related_measure_data
    related = factories.MeasureFactory.create(**related_data)

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME32(related.transaction).validate(related)


# -- Ceiling/quota definition existence


def test_ME10():
    """
    The order number must be specified if the "order number flag" (specified in
    the measure type record) has the value "mandatory".

    If the flag is set to "not permitted" then the field cannot be entered.
    """
    measure = factories.MeasureFactory.create(
        measure_type__order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
        order_number=None,
        dead_order_number=None,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME10(measure.transaction).validate(measure)

    measure = factories.MeasureFactory.create(
        measure_type__order_number_capture_code=OrderNumberCaptureCode.NOT_PERMITTED,
        order_number=factories.QuotaOrderNumberFactory.create(),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME10(measure.transaction).validate(measure)


@only_applicable_after("2007-12-31")
def test_ME116(date_ranges):
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """
    measure = factories.MeasureWithQuotaFactory.create(
        order_number__valid_between=date_ranges.starts_with_normal,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME116(measure.transaction).validate(measure)


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
    measure = factories.MeasureWithQuotaFactory.create(
        order_number=origin.order_number,
        geographical_area=factories.GeographicalAreaFactory.create(),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME117(measure.transaction).validate(measure)

    measure = factories.MeasureWithQuotaFactory.create(
        order_number=origin.order_number,
        geographical_area=origin.geographical_area,
    )

    business_rules.ME117(measure.transaction).validate(measure)


@pytest.mark.skip(reason="Duplicate of ME116")
def test_ME118():
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    assert False


@only_applicable_after("2007-12-31")
def test_ME119(date_ranges):
    """
    When a quota order number is used in a measure then the validity period of
    the quota order number origin must span the validity period of the measure.

    This rule is only applicable for measures with start date after 31/12/2007.
    """

    measure = factories.MeasureWithQuotaFactory.create(
        order_number__origin__valid_between=date_ranges.starts_with_normal,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME119(measure.transaction).validate(measure)


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

    measure = factories.MeasureFactory.create(
        additional_code=additional_code,
        goods_nomenclature=goods_nomenclature,
    )

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ME9(measure.transaction).validate(measure)


def test_ME12():
    """If the additional code is specified then the additional code type must
    have a relationship with the measure type."""

    measure = factories.MeasureFactory.create(
        additional_code=factories.AdditionalCodeFactory.create(),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME12(measure.transaction).validate(measure)

    rel = factories.AdditionalCodeTypeMeasureTypeFactory.create()
    measure = factories.MeasureFactory.create(
        measure_type=rel.measure_type,
        additional_code__type=rel.additional_code_type,
        goods_nomenclature__item_id="7700000000",
    )

    business_rules.ME12(measure.transaction).validate(measure)


def test_ME12_after_measure_type_updated():
    additional_code = factories.AdditionalCodeFactory.create()
    measure_type = factories.MeasureTypeFactory.create()
    factories.AdditionalCodeTypeMeasureTypeFactory.create(
        measure_type=measure_type,
        additional_code_type=additional_code.type,
    )
    measure_type = measure_type.new_version(measure_type.transaction.workbasket)
    measure = factories.MeasureFactory.create(
        measure_type=measure_type,
        additional_code=additional_code,
    )

    business_rules.ME12(measure.transaction).validate(measure)


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
            business_rules.ME17(measure.transaction).validate(measure)


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
            business_rules.ME24(measure.transaction).validate(measure)


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
    measure = factories.MeasureFactory.create(
        generating_regulation__valid_between=date_ranges.starts_with_normal,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME87(measure.transaction).validate(measure)

    # implicit - regulation end date supercedes measure end date
    # generating reg:  s---x
    # measure:         s---i----x       i = implicit end date
    measure = factories.MeasureFactory.create(
        generating_regulation__valid_between=date_ranges.starts_with_normal,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME87(measure.transaction).validate(measure)


@pytest.mark.skip(
    reason="Abrogation, modification and replacement regulations are not used",
)
def test_ME26():
    """The entered regulation may not be completely abrogated."""


def test_ME27(spanning_dates):
    """The entered regulation may not be fully replaced."""
    replacement_dates, regulation_dates, fully_spanned = spanning_dates

    measure = factories.MeasureFactory.create(
        generating_regulation=factories.ReplacementFactory.create(
            enacting_regulation__valid_between=replacement_dates,
            target_regulation__valid_between=regulation_dates,
        ).target_regulation,
    )

    with raises_if(BusinessRuleViolation, fully_spanned):
        business_rules.ME27(measure.transaction).validate(measure)


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


@pytest.mark.parametrize(
    ("terminating_regulation", "error_expected"),
    (
        (False, False),
        (True, True),
    ),
)
@factory.django.mute_signals(signals.pre_save)
def test_ME33(terminating_regulation, date_ranges, error_expected):
    """
    A justification regulation may not be entered if the measure end date is not
    filled in.

    A justification regulation is used to ‘justify’ terminating a regulation.
    There is no requirement for this in UK law, nor for audit purposes in the UK
    tariff, however it is a mandatory field in the database and in CDS. The rule
    is self-explanatory: if there no end date on the measure, then the
    justification regulation field must be set to null.
    """
    regulation = factories.RegulationFactory.create()
    measure = factories.MeasureFactory.create(
        valid_between=date_ranges.no_end,
        generating_regulation=regulation,
        terminating_regulation=(regulation if terminating_regulation else None),
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME33(measure.transaction).validate(measure)


@pytest.mark.parametrize(
    ("terminating_regulation", "error_expected"),
    (
        (True, False),
        (False, True),
    ),
)
@factory.django.mute_signals(signals.pre_save)
def test_ME34(terminating_regulation, date_ranges, error_expected):
    """
    A justification regulation must be entered if the measure end date is filled
    in.

    The justification regulation fields MUST be completed when the regulation is end-dated.
    - Users should be discouraged from end dating regulations, instead they should end
      date measures.
    - Always use the measure generating regulation ID and role to populate the
      justification equivalents, if the end date needs to be entered on a regulation.
    """
    regulation = factories.RegulationFactory.create()
    measure = factories.MeasureFactory.create(
        valid_between=date_ranges.normal,
        generating_regulation=regulation,
        terminating_regulation=(regulation if terminating_regulation else None),
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME34(measure.transaction).validate(measure)


# -- Measure component


@pytest.mark.parametrize(
    ("applicability_code", "component", "condition_component", "error_expected"),
    [
        (ApplicabilityCode.MANDATORY, False, False, True),
        (ApplicabilityCode.MANDATORY, True, False, False),
        (ApplicabilityCode.MANDATORY, False, True, False),
        (ApplicabilityCode.MANDATORY, True, True, True),
        (ApplicabilityCode.NOT_PERMITTED, True, False, True),
        (ApplicabilityCode.NOT_PERMITTED, False, True, True),
        (ApplicabilityCode.NOT_PERMITTED, True, True, True),
        (ApplicabilityCode.NOT_PERMITTED, False, False, False),
        (ApplicabilityCode.PERMITTED, False, False, False),
        (ApplicabilityCode.PERMITTED, True, False, False),
        (ApplicabilityCode.PERMITTED, False, True, False),
        (ApplicabilityCode.PERMITTED, True, True, True),
    ],
)
def test_ME40(applicability_code, component, condition_component, error_expected):
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

    measure = factories.MeasureFactory.create(
        measure_type__measure_component_applicability_code=applicability_code,
    )

    if component:
        component = factories.MeasureComponentFactory.create(component_measure=measure)

    if condition_component:
        condition_component = factories.MeasureConditionComponentFactory.create(
            condition__dependent_measure=measure,
        )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME40(
            (condition_component or component or measure).transaction,
        ).validate(measure)


def test_ME41(reference_nonexistent_record):
    """The referenced duty expression must exist."""

    with reference_nonexistent_record(
        factories.MeasureComponentFactory,
        "duty_expression",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME41(component.transaction).validate(component)


def test_ME42(assert_spanning_enforced):
    """The validity period of the duty expression must span the validity period
    of the measure."""
    assert_spanning_enforced(
        factories.MeasureComponentFactory,
        business_rules.ME42,
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
        business_rules.ME43(component.transaction).validate(component)


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
    component = factories.MeasureComponentFactory.create(
        component_measure=measure,
        duty_expression__duty_amount_applicability_code=applicability_code,
        duty_amount=amount,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME45(component.transaction).validate(measure)


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
    component = factories.MeasureComponentFactory.create(
        component_measure=measure,
        duty_expression__monetary_unit_applicability_code=applicability_code,
        monetary_unit=monetary_unit,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME46(component.transaction).validate(measure)


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
    component = factories.MeasureComponentWithMeasurementFactory.create(
        component_measure=measure,
        duty_expression__measurement_unit_applicability_code=applicability_code,
        component_measurement=measurement,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME47(component.transaction).validate(measure)


def test_ME48(reference_nonexistent_record):
    """The referenced monetary unit must exist."""

    with reference_nonexistent_record(
        factories.MeasureComponentWithMonetaryUnitFactory,
        "monetary_unit",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME48(component.transaction).validate(component)


def test_ME49(assert_spanning_enforced):
    """The validity period of the referenced monetary unit must span the
    validity period of the measure."""
    assert_spanning_enforced(
        factories.MeasureComponentWithMonetaryUnitFactory,
        business_rules.ME49,
    )


def test_ME50(reference_nonexistent_record):
    """The combination measurement unit + measurement unit qualifier must
    exist."""

    with reference_nonexistent_record(
        factories.MeasureComponentWithMeasurementFactory,
        "component_measurement",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME50(component.transaction).validate(component)


def test_ME51(assert_spanning_enforced):
    """The validity period of the measurement unit must span the validity period
    of the measure."""
    assert_spanning_enforced(
        factories.MeasureComponentWithMeasurementFactory,
        business_rules.ME51,
    )


def test_ME52(assert_spanning_enforced):
    """The validity period of the measurement unit qualifier must span the
    validity period of the measure."""
    assert_spanning_enforced(
        factories.MeasureComponentWithMeasurementFactory,
        business_rules.ME52,
    )


# -- Measure condition and Measure condition component


def test_ME53(reference_nonexistent_record):
    """The referenced measure condition must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionComponentFactory,
        "condition",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME53(component.transaction).validate(component)


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

    def delete_certificate(c):
        c.get_descriptions(transaction=c.transaction).first().delete()
        c.delete()

    with reference_nonexistent_record(
        factories.MeasureConditionWithCertificateFactory,
        "required_certificate",
        delete_certificate,
    ) as condition:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME56(condition.transaction).validate(condition)


def test_ME57(assert_spanning_enforced):
    """The validity period of the referenced certificate must span the validity
    period of the measure."""
    assert_spanning_enforced(
        factories.MeasureConditionWithCertificateFactory,
        business_rules.ME57,
    )


@pytest.mark.parametrize("existing_cert", (True, False))
@pytest.mark.parametrize("existing_volume", (True, False))
@pytest.mark.parametrize("existing_unit", (True, False))
@pytest.mark.parametrize("existing_currency", (True, False))
@pytest.mark.parametrize("duplicate_cert", (True, False))
@pytest.mark.parametrize("duplicate_volume", (True, False))
@pytest.mark.parametrize("duplicate_unit", (True, False))
@pytest.mark.parametrize("duplicate_currency", (True, False))
def test_ME58(
    existing_cert: bool,
    existing_volume: bool,
    existing_unit: bool,
    existing_currency: bool,
    duplicate_cert: bool,
    duplicate_volume: bool,
    duplicate_unit: bool,
    duplicate_currency: bool,
):
    """
    The same certificate can only be referenced once by the same measure and the
    same condition type.

    Although the rule only mentions certificates, we have extended it to cover
    volumes and units as well. Thus, it now checks that each combination of
    certificate, volume and unit is unique, including where all are missing.

    Volume and unit should always come together, and the same volume under a
    different unit is allowed. So e.g. 20.000 KGM and 20.000 TNE is valid.

    Note that it is not really meant to be possible to have a certificate and a
    volume and unit, but that should be enforced elsewhere so this test checks
    for it anyway.
    """
    expect_error = (
        (existing_cert == duplicate_cert)
        and (existing_volume == duplicate_volume)
        and (existing_unit == duplicate_unit)
        and (existing_currency == duplicate_currency)
    )

    cert = factories.CertificateFactory.create()
    volume = factories.duty_amount().function()
    unit = factories.MeasurementFactory.create()
    currency = factories.MonetaryUnitFactory.create()

    existing = factories.MeasureConditionFactory.create(
        required_certificate=(cert if existing_cert else None),
        duty_amount=(volume if existing_volume else None),
        condition_measurement=(unit if existing_unit else None),
        monetary_unit=(currency if existing_currency else None),
    )
    duplicate = factories.MeasureConditionFactory.create(
        condition_code=existing.condition_code,
        dependent_measure=existing.dependent_measure,
        required_certificate=(cert if duplicate_cert else None),
        duty_amount=(volume if duplicate_volume else None),
        condition_measurement=(unit if duplicate_unit else None),
        monetary_unit=(currency if duplicate_currency else None),
    )

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ME58(duplicate.transaction).validate(existing)

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ME58(duplicate.transaction).validate(duplicate)


def test_ME59(reference_nonexistent_record):
    """The referenced action code must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionFactory,
        "action",
    ) as condition:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME59(condition.transaction).validate(condition)


def test_ME60(reference_nonexistent_record):
    """The referenced monetary unit must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionFactory,
        "monetary_unit",
    ) as condition:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME60(condition.transaction).validate(condition)


def test_ME61(assert_spanning_enforced):
    """The validity period of the referenced monetary unit must span the
    validity period of the measure."""
    assert_spanning_enforced(
        factories.MeasureConditionFactory,
        business_rules.ME61,
    )


def test_ME62(reference_nonexistent_record):
    """The combination measurement unit + measurement unit qualifier must
    exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionWithMeasurementFactory,
        "condition_measurement",
    ) as condition:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME62(condition.transaction).validate(condition)


def test_ME63(assert_spanning_enforced):
    """The validity period of the measurement unit must span the validity period
    of the measure."""
    assert_spanning_enforced(
        factories.MeasureConditionWithMeasurementFactory,
        business_rules.ME63,
    )


def test_ME64(assert_spanning_enforced):
    """The validity period of the measurement unit qualifier must span the
    validity period of the measure."""
    assert_spanning_enforced(
        factories.MeasureConditionWithMeasurementFactory,
        business_rules.ME64,
    )


def test_ME105(reference_nonexistent_record):
    """The referenced duty expression must exist."""

    with reference_nonexistent_record(
        factories.MeasureConditionComponentFactory,
        "duty_expression",
    ) as component:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME105(component.transaction).validate(component)


def test_ME106(assert_spanning_enforced):
    """The validity period of the duty expression must span the validity period
    of the measure."""
    assert_spanning_enforced(
        factories.MeasureConditionComponentFactory,
        business_rules.ME106,
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

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ME108(component.transaction).validate(component)


# Even if a ConditionCode can accept either a certificate or a price,
# a Condition should not be able to accept both at once
@pytest.mark.parametrize(
    "accepts_certificate, accepts_price",
    [
        (True, True),  # Some ConditionCodes (e.g. 'E') accept both
        (True, False),
        (False, True),
    ],
)
def test_ConditionCodeAcceptance_certificate_and_price(
    accepts_certificate,
    accepts_price,
):
    certificate = factories.CertificateFactory.create()
    code = factories.MeasureConditionCodeFactory(
        accepts_certificate=accepts_certificate,
        accepts_price=accepts_price,
    )
    condition = factories.MeasureConditionFactory.create(
        duty_amount=1.000,
        required_certificate=certificate,
        condition_code=code,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ConditionCodeAcceptance(condition.transaction).validate(
            condition,
        )


@pytest.mark.parametrize(
    "accepts_certificate, accepts_price, expect_error",
    [
        (False, True, True),
        (False, False, True),
        (True, True, False),  # Some ConditionCodes (e.g. 'E') accept both
        (True, False, False),
    ],
)
def test_ConditionCodeAcceptance_certificate(
    accepts_certificate,
    accepts_price,
    expect_error,
):
    certificate = factories.CertificateFactory.create()
    code = factories.MeasureConditionCodeFactory.create(
        accepts_certificate=accepts_certificate,
        accepts_price=accepts_price,
    )
    condition = factories.MeasureConditionFactory.create(
        required_certificate=certificate,
        duty_amount=None,
        condition_code=code,
    )
    print(condition.duty_amount)

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ConditionCodeAcceptance(condition.transaction).validate(
            condition,
        )


@pytest.mark.parametrize(
    "accepts_certificate, accepts_price, expect_error",
    [
        (True, False, True),
        (False, False, True),
        (True, True, False),  # Some ConditionCodes (e.g. 'E') accept both
        (False, True, False),
    ],
)
def test_ConditionCodeAcceptance_price(
    accepts_certificate,
    accepts_price,
    expect_error,
):
    code = factories.MeasureConditionCodeFactory.create(
        accepts_certificate=accepts_certificate,
        accepts_price=accepts_price,
    )
    condition = factories.MeasureConditionFactory.create(
        duty_amount=1.000,
        condition_code=code,
    )

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ConditionCodeAcceptance(condition.transaction).validate(
            condition,
        )


# This is possible for Condition codes (e.g. 'W') that accept neither certificates nor price
def test_ConditionCodeAcceptance_nothing_added():
    code = factories.MeasureConditionCodeFactory.create()
    condition = factories.MeasureConditionFactory.create(
        duty_amount=None,
        condition_code=code,
    )
    business_rules.ConditionCodeAcceptance(condition.transaction).validate(condition)


@pytest.mark.parametrize(
    "requires_duty, duty_amount, expect_error",
    [
        (True, None, True),
        (True, 1.000, False),
        (False, None, False),
        (
            False,
            1.000,
            True,
        ),
    ],
)
def test_ActionRequiresDuty(requires_duty, duty_amount, expect_error):
    condition = factories.MeasureConditionFactory.create(
        action__requires_duty=requires_duty,
    )
    factories.MeasureConditionComponentFactory.create(
        condition=condition,
        duty_amount=duty_amount,
        transaction=condition.transaction,
    )

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ActionRequiresDuty(condition.transaction).validate(condition)


def test_ActionRequiresDuty_ignores_outdated_components():
    condition = factories.MeasureConditionFactory.create(action__requires_duty=True)
    component = factories.MeasureConditionComponentFactory.create(
        condition=condition,
        duty_amount=1.000,
        transaction=condition.transaction,
    )
    component.new_version(
        component.transaction.workbasket,
        transaction=condition.transaction,
        duty_amount=None,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ActionRequiresDuty(condition.transaction).validate(condition)


@pytest.mark.parametrize(
    ("applicability_code", "amount", "error_expected"),
    [
        (ApplicabilityCode.MANDATORY, None, True),
        (ApplicabilityCode.MANDATORY, Decimal(1), False),
        (ApplicabilityCode.NOT_PERMITTED, Decimal(1), True),
        (ApplicabilityCode.NOT_PERMITTED, None, False),
        (ApplicabilityCode.PERMITTED, Decimal(1), False),
        (ApplicabilityCode.PERMITTED, None, False),
    ],
)
def test_ME109(applicability_code, amount, error_expected):
    """
    If the flag 'amount' on duty expression is 'mandatory' then an amount must
    be specified.

    If the flag is set to 'not permitted' then no amount may be entered.
    """

    measure = factories.MeasureFactory.create()
    condition = factories.MeasureConditionComponentFactory.create(
        condition__dependent_measure=measure,
        duty_expression__duty_amount_applicability_code=applicability_code,
        duty_amount=amount,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME109(condition.transaction).validate(measure)


@pytest.mark.parametrize(
    ("applicability_code", "monetary_unit", "error_expected"),
    [
        (ApplicabilityCode.MANDATORY, False, True),
        (ApplicabilityCode.MANDATORY, True, False),
        (ApplicabilityCode.NOT_PERMITTED, True, True),
        (ApplicabilityCode.NOT_PERMITTED, False, False),
        (ApplicabilityCode.PERMITTED, True, False),
        (ApplicabilityCode.PERMITTED, False, False),
    ],
)
def test_ME110(applicability_code, monetary_unit, error_expected):
    """
    If the flag 'monetary unit' on duty expression is 'mandatory' then a
    monetary unit must be specified.

    If the flag is set to 'not permitted' then no monetary unit may be entered.
    """

    monetary_unit = factories.MonetaryUnitFactory.create() if monetary_unit else None

    measure = factories.MeasureFactory.create()
    condition = factories.MeasureConditionComponentFactory.create(
        condition__dependent_measure=measure,
        duty_expression__monetary_unit_applicability_code=applicability_code,
        monetary_unit=monetary_unit,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME110(condition.transaction).validate(measure)


@pytest.mark.parametrize(
    ("applicability_code", "measurement", "error_expected"),
    [
        (ApplicabilityCode.MANDATORY, False, True),
        (ApplicabilityCode.MANDATORY, True, False),
        (ApplicabilityCode.NOT_PERMITTED, True, True),
        (ApplicabilityCode.NOT_PERMITTED, False, False),
        (ApplicabilityCode.PERMITTED, True, False),
        (ApplicabilityCode.PERMITTED, False, False),
    ],
)
def test_ME111(applicability_code, measurement, error_expected):
    """
    If the flag 'measurement unit' on duty expression is 'mandatory' then a
    measurement unit must be specified.

    If the flag is set to 'not permitted' then no measurement unit may be
    entered.
    """

    measurement = factories.MeasurementFactory.create() if measurement else None

    measure = factories.MeasureFactory.create()
    condition = factories.MeasureConditionComponentWithMeasurementFactory.create(
        condition__dependent_measure=measure,
        duty_expression__measurement_unit_applicability_code=applicability_code,
        component_measurement=measurement,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME111(condition.transaction).validate(measure)


# -- Measure excluded geographical area


@pytest.mark.parametrize(
    ("area_code", "error_expected"),
    (
        (AreaCode.COUNTRY, True),
        (AreaCode.REGION, True),
        (AreaCode.GROUP, False),
    ),
)
def test_ME65(area_code, error_expected):
    """An exclusion can only be entered if the measure is applicable to a geographical
    area group (area code = 1)."""

    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        modified_measure__geographical_area__area_code=area_code,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME65(exclusion.transaction).validate(exclusion)


def test_ME66():
    """The excluded geographical area must be a member of the geographical area
    group."""

    membership = factories.GeographicalMembershipFactory.create()
    measure = factories.MeasureFactory.create(geographical_area=membership.geo_group)

    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        modified_measure=measure,
        excluded_geographical_area=membership.member,
    )

    business_rules.ME66(exclusion.transaction).validate(exclusion)

    deleted = factories.GeographicalMembershipFactory.create(
        geo_group=membership.geo_group,
        member=membership.member,
        version_group=membership.version_group,
        update_type=UpdateType.DELETE,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME66(deleted.transaction).validate(exclusion)

    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        modified_measure=measure,
        excluded_geographical_area=factories.GeographicalAreaFactory.create(),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME66(exclusion.transaction).validate(exclusion)


def test_ME67(spanning_dates):
    """The membership period of the excluded geographical area must span the
    validity period of the measure."""
    membership_period, measure_period, fully_spans = spanning_dates

    membership = factories.GeographicalMembershipFactory.create(
        valid_between=membership_period,
    )
    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership.member,
        modified_measure__geographical_area=membership.geo_group,
        modified_measure__valid_between=measure_period,
    )
    with raises_if(BusinessRuleViolation, not fully_spans):
        business_rules.ME67(exclusion.transaction).validate(exclusion)


def test_ME68():
    """The same geographical area can only be excluded once by the same
    measure."""

    existing = factories.MeasureExcludedGeographicalAreaFactory.create()

    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=existing.excluded_geographical_area,
        modified_measure=existing.modified_measure,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME68(exclusion.transaction).validate(existing)


# -- Footnote association


def test_ME69(reference_nonexistent_record):
    """The associated footnote must exist."""

    with reference_nonexistent_record(
        factories.FootnoteAssociationMeasureFactory,
        "associated_footnote",
    ) as assoc:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ME69(assoc.transaction).validate(assoc)


def test_ME70():
    """The same footnote can only be associated once with the same measure."""

    existing = factories.FootnoteAssociationMeasureFactory.create()
    business_rules.ME70(existing.transaction).validate(existing)

    assoc = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=existing.footnoted_measure,
        associated_footnote=existing.associated_footnote,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ME70(assoc.transaction).validate(assoc)


@pytest.mark.parametrize(
    ("application_code", "item_id", "error_expected"),
    (
        (ApplicationCode.CN_MEASURES, "0123456789", True),
        (ApplicationCode.CN_MEASURES, "0123456700", False),
        (ApplicationCode.OTHER_MEASURES, "0123456789", False),
        (ApplicationCode.OTHER_MEASURES, "0123456700", False),
        (ApplicationCode.DYNAMIC_FOOTNOTE, "0123456789", False),
        (ApplicationCode.DYNAMIC_FOOTNOTE, "0123456700", False),
    ),
)
def test_ME71_ME72(application_code, item_id, error_expected):
    """Footnotes with a footnote type for which the application type = "CN
    footnotes" cannot be associated with TARIC codes (codes with pos. 9-10
    different from 00). Footnotes with a footnote type for which the application
    type = "measure footnotes" can be associated at any level."""

    assoc = factories.FootnoteAssociationMeasureFactory.create(
        associated_footnote__footnote_type__application_code=application_code,
        footnoted_measure__goods_nomenclature__item_id=item_id,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.ME71(assoc.transaction).validate(assoc)


def test_ME73(assert_spanning_enforced):
    """The validity period of the associated footnote must span the validity
    period of the measure."""
    assert_spanning_enforced(
        factories.FootnoteAssociationMeasureFactory,
        business_rules.ME73,
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
    business_rules.ME104(measure.transaction).validate(measure)

    measure.terminating_regulation = factories.RegulationFactory.create()
    with pytest.raises(BusinessRuleViolation):
        business_rules.ME104(measure.transaction).validate(measure)


def test_measurement_unit_qualifier_is_optional():
    """In TARIC measurement unit qualifiers do not have to be used on every
    measure."""
    factories.MeasurementFactory.create(measurement_unit_qualifier=None)


def test_unique_identifying_fields(assert_handles_duplicates):
    assert_handles_duplicates(
        factories.MeasureFactory,
        UniqueIdentifyingFields,
    )
