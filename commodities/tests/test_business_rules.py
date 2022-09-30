import pytest
from django.db import DataError

from checks.tasks import check_transaction_sync
from commodities import business_rules
from common.business_rules import BusinessRuleViolation
from common.models.utils import override_current_transaction
from common.tests import factories
from common.tests.util import raises_if
from common.validators import UpdateType
from footnotes.validators import ApplicationCode

pytestmark = pytest.mark.django_db


@pytest.mark.xfail(reason="NIG1 disabled")
def test_NIG1(date_ranges):
    """The validity period of the goods nomenclature must not overlap any other
    goods nomenclature with the same SID."""

    good = factories.GoodsNomenclatureFactory.create()
    business_rules.NIG1(good.transaction).validate(good)

    non_overlapping = factories.GoodsNomenclatureFactory.create(
        sid=good.sid,
        valid_between=date_ranges.adjacent_earlier,
    )
    business_rules.NIG1(non_overlapping.transaction).validate(non_overlapping)

    duplicate = factories.GoodsNomenclatureFactory.create(
        sid=good.sid,
        valid_between=good.valid_between,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG1(duplicate.transaction).validate(duplicate)


@pytest.mark.parametrize(
    ("parent_validity", "self_validity", "child_validity", "expect_error"),
    (
        ("normal", "no_end", "no_end", True),
        ("no_end", "normal", "no_end", False),  # see note on NIG2
        ("no_end", "no_end", "normal", False),
        ("no_end", "no_end", "no_end", False),
        ("normal", "normal", "normal", False),
    ),
    ids=(
        "parent_does_not_span_self",
        "self_does_not_span_child",
        "child_can_end_sooner",
        "all_open_ended",
        "all_closed_and_span",
    ),
)
def test_NIG2(
    date_ranges,
    parent_validity,
    self_validity,
    child_validity,
    expect_error,
):
    """
    The validity period of the goods nomenclature must be within the validity
    period of the product line above in the hierarchy.

    Also covers NIG3
    """
    parent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            parent_validity,
        ),
        indented_goods_nomenclature__item_id="2901000000",
        indent=0,
    )
    self = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(date_ranges, self_validity),
        indented_goods_nomenclature__item_id="2901210000",
        indent=1,
    )
    child = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__item_id="2901290000",
        indented_goods_nomenclature__valid_between=getattr(date_ranges, child_validity),
        indent=2,
    )

    # Running against a lone code should never error
    business_rules.NIG2(parent.transaction).validate(parent)

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.NIG2(type(child.transaction).objects.last()).validate(self)


def test_NIG2_only_checks_future_dates_of_parent(date_ranges):
    """
    The validity period of the goods nomenclature must be within the validity
    period of the product line above in the hierarchy.

    Also covers NIG3
    """

    parent_1 = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            "starts_delta_no_end",
        ),
        indented_goods_nomenclature__item_id="2901000000",
        indent=0,
    )

    child = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            "starts_1_month_ago_no_end",
        ),
        indented_goods_nomenclature__item_id="2901210000",
        indent=1,
    )

    with raises_if(BusinessRuleViolation, False):
        business_rules.NIG2(type(child.transaction).objects.last()).validate(child)


def test_NIG2_is_valid_with_multiple_parents_spanning_child_valid_period(date_ranges):
    grand_parent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            "starts_delta_no_end",
        ),
        indented_goods_nomenclature__item_id="2901000000",
        indent=0,
    )

    distant_parent_1 = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            "starts_2_months_ago_to_delta",
        ),
        indented_goods_nomenclature__item_id="2901200000",
        indent=1,
    )

    distant_parent_2 = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            "starts_1_month_ago_no_end",
        ),
        indented_goods_nomenclature__item_id="2901400000",
        indent=1,
    )

    parent_closest = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            "starts_1_month_ago_to_1_month_ahead",
        ),
        indented_goods_nomenclature__item_id="2901500000",
        indent=1,
    )

    not_a_parent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            "starts_1_month_ago_no_end",
        ),
        indented_goods_nomenclature__item_id="2901700000",
        indent=1,
    )

    child = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=getattr(
            date_ranges,
            "starts_1_month_ago_no_end",
        ),
        indented_goods_nomenclature__item_id="2901510000",
        indent=2,
    )

    with raises_if(BusinessRuleViolation, False):
        business_rules.NIG2(type(child.transaction).objects.last()).validate(child)


@pytest.mark.parametrize(
    ("parent_validities", "child_validity", "expected"),
    (
        (
            [
                "starts_1_month_ago_to_delta",
                "starts_delta_to_1_month_ahead",
            ],
            "starts_1_month_ago_to_1_month_ahead",
            True,
        ),
        (
            [
                "starts_1_month_ago_no_end",
                "starts_2_months_ago_to_delta",
            ],
            "starts_1_month_ago_to_1_month_ahead",
            True,
        ),
        (
            [
                "starts_2_months_ago_to_1_month_ago",
                "starts_1_month_ahead_to_2_months_ahead",
            ],
            "starts_1_month_ago_to_1_month_ahead",
            False,
        ),
        (
            [
                "starts_2_months_ago_to_1_month_ago",
                "starts_1_month_ahead_to_2_months_ahead",
                "starts_1_month_ago_no_end",
            ],
            "starts_1_month_ago_to_1_month_ahead",
            True,
        ),
        (
            [
                "starts_2_months_ago_to_1_month_ago",
                "starts_1_month_ahead_to_2_months_ahead",
            ],
            "starts_1_month_ago_no_end",
            False,
        ),
        (
            [
                "starts_1_month_ago_no_end",
            ],
            "starts_1_month_ago_no_end",
            True,
        ),
        (
            [
                "starts_1_month_ago_no_end",
            ],
            "starts_2_months_ago_to_1_month_ago",
            False,
        ),
        (
            [
                "starts_1_month_ago_no_end",
            ],
            "starts_1_month_ago_to_delta",
            True,
        ),
    ),
)
def test_NIG2_parents_span_child_valid(
    date_ranges,
    parent_validities,
    child_validity,
    expected,
):
    target = business_rules.NIG2().parents_span_child
    good = factories.GoodsNomenclatureFactory.create()
    parents = []

    for parent_validity in parent_validities:
        validity = getattr(date_ranges, parent_validity)
        parent = factories.GoodsNomenclatureFactory.create(
            sid=good.sid,
            valid_between=validity,
        )
        parents.append(parent)

    child = factories.GoodsNomenclatureFactory.create(
        sid=good.sid,
        valid_between=getattr(date_ranges, child_validity),
    )

    assert target(parents, child) == expected


def test_NIG4(date_ranges):
    """The start date of the goods nomenclature must be less than or equal to
    the end date."""

    with pytest.raises(DataError):
        factories.GoodsNomenclatureFactory.create(valid_between=date_ranges.backwards)


def test_NIG5(workbasket):
    """
    When creating a goods nomenclature code, an origin must exist.

    This rule is only applicable to update extractions.
    """
    origin = factories.GoodsNomenclatureFactory.create(item_id="2000000000")
    bad_good = factories.GoodsNomenclatureFactory.create(
        item_id="2000000010",
        origin=None,
        indent__indent=1,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG5(bad_good.transaction).validate(bad_good)

    deleted_good = bad_good.new_version(workbasket, update_type=UpdateType.DELETE)
    business_rules.NIG5(deleted_good.transaction).validate(deleted_good)

    good_good = factories.GoodsNomenclatureFactory.create(
        origin__derived_from_goods_nomenclature=origin,
        indent__indent=1,
    )
    business_rules.NIG5(good_good.transaction).validate(good_good)


@pytest.mark.parametrize(
    "valid_between, expect_error",
    [
        ("later", True),
        ("earlier", True),
        ("adjacent_earlier", True),
        ("normal", True),
        ("overlap_normal", False),
        ("adjacent_later", False),
    ],
)
def test_NIG7(date_ranges, valid_between, expect_error):
    """The origin must be applicable the day before the start date of the new
    code entered."""
    origin = factories.GoodsNomenclatureOriginFactory.create(
        derived_from_goods_nomenclature__valid_between=date_ranges.normal,
        new_goods_nomenclature__valid_between=getattr(
            date_ranges,
            valid_between,
        ),
    )

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.NIG7(origin.transaction).validate(origin)


@pytest.mark.parametrize(
    ("valid_between", "expect_error"),
    [
        ("later", True),
        ("earlier", True),
        ("no_end", True),
        ("adjacent_earlier", False),
        ("overlap_normal_earlier", False),
    ],
)
def test_NIG10(date_ranges, update_type, valid_between, expect_error):
    """The successor must be applicable the day after the end date of the old
    code."""
    successor = factories.GoodsNomenclatureSuccessorFactory.create(
        absorbed_into_goods_nomenclature__valid_between=date_ranges.normal,
        replaced_goods_nomenclature__valid_between=getattr(
            date_ranges,
            valid_between,
        ),
        update_type=update_type,
    )

    expect_error = expect_error and update_type != UpdateType.DELETE
    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.NIG10(successor.transaction).validate(successor)


def test_NIG11_one_indent_mandatory():
    """At least one indent record is mandatory."""

    good = factories.GoodsNomenclatureFactory.create(indent=None)
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11(good.transaction).validate(good)


def test_NIG11_first_indent_must_have_same_start_date(date_ranges):
    """The start date of the first indentation must be equal to the start date
    of the nomenclature."""

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=date_ranges.normal,
        validity_start=date_ranges.overlap_normal.lower,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11(indent.transaction).validate(
            indent.indented_goods_nomenclature,
        )


def test_NIG11_no_overlapping_indents():
    """No two associated indentations may have the same start date."""

    existing = factories.GoodsNomenclatureIndentFactory.create()
    duplicate = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=existing.indented_goods_nomenclature,
        validity_start=existing.validity_start,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11(duplicate.transaction).validate(
            existing.indented_goods_nomenclature,
        )


def test_NIG11_start_date_less_than_end_date(date_ranges):
    """The start date must be less than or equal to the end date of the
    nomenclature."""

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=date_ranges.normal,
        validity_start=date_ranges.later.lower,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11(indent.transaction).validate(
            indent.indented_goods_nomenclature,
        )


def test_NIG12_one_description_mandatory():
    """At least one description record is mandatory."""
    good = factories.GoodsNomenclatureFactory.create(description=None)
    with override_current_transaction(good.transaction):
        with pytest.raises(BusinessRuleViolation):
            business_rules.NIG12(good.transaction).validate(good)


def test_NIG12_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start
    date of the nomenclature."""
    good = factories.GoodsNomenclatureFactory.create(
        description__validity_start=date_ranges.later.lower,
    )
    with override_current_transaction(good.transaction):
        with pytest.raises(BusinessRuleViolation):
            business_rules.NIG12(good.transaction).validate(good)


def test_NIG12_start_dates_cannot_match():
    """No two associated description periods may have the same start date."""

    goods_nomenclature = factories.GoodsNomenclatureFactory.create()
    duplicate = factories.GoodsNomenclatureDescriptionFactory.create(
        described_goods_nomenclature=goods_nomenclature,
        validity_start=goods_nomenclature.valid_between.lower,
    )
    with override_current_transaction(duplicate.transaction):
        with pytest.raises(BusinessRuleViolation):
            business_rules.NIG12(duplicate.transaction).validate(goods_nomenclature)


def test_NIG12_description_start_before_nomenclature_end(
    date_ranges,
    unapproved_transaction,
):
    """The start date must be less than or equal to the end date of the
    nomenclature."""

    goods_nomenclature = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
        description__validity_start=date_ranges.starts_with_normal.lower,
        transaction=unapproved_transaction,
    )
    early_description = factories.GoodsNomenclatureDescriptionFactory.create(
        described_goods_nomenclature=goods_nomenclature,
        validity_start=date_ranges.later.lower,
    )
    with override_current_transaction(early_description.transaction):
        with pytest.raises(BusinessRuleViolation):
            business_rules.NIG12(early_description.transaction).validate(
                goods_nomenclature,
            )


def test_NIG12_direct_rule_called_for_goods():
    good = factories.GoodsNomenclatureFactory.create(description=None)
    check_transaction_sync(good.transaction)

    assert (
        good.transaction.checks.get()
        .model_checks.filter(
            message__contains="At least one description record is mandatory.",
        )
        .exists()
    )


@pytest.mark.parametrize(
    ("application_code", "item_id", "error_expected"),
    (
        (ApplicationCode.CN_NOMENCLATURE, "0123456789", True),
        (ApplicationCode.CN_NOMENCLATURE, "0123456700", False),
        (ApplicationCode.TARIC_NOMENCLATURE, "0123456789", False),
        (ApplicationCode.TARIC_NOMENCLATURE, "0123456700", False),
        (ApplicationCode.DYNAMIC_FOOTNOTE, "0123456789", False),
        (ApplicationCode.DYNAMIC_FOOTNOTE, "0123456700", False),
    ),
)
def test_NIG18_NIG19(application_code, item_id, error_expected):
    """Footnotes with a footnote type for which the application type = "CN
    footnotes" must be linked to CN lines (all codes up to 8 digits). Footnotes
    with a footnote type for which the application type = "TARIC footnotes" can
    be associated at any level."""

    assoc = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote__footnote_type__application_code=application_code,
        goods_nomenclature__item_id=item_id,
    )

    with raises_if(BusinessRuleViolation, error_expected):
        business_rules.NIG18(assoc.transaction).validate(assoc)


def test_NIG21(date_ranges):
    """The start date of the association with a footnote must be less than or
    equal to the end date of the association."""

    with pytest.raises(DataError):
        factories.FootnoteAssociationGoodsNomenclatureFactory.create(
            valid_between=date_ranges.backwards,
        )


def test_NIG22(date_ranges):
    """The period of the association with a footnote must be within the validity
    period of the nomenclature."""
    association = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        goods_nomenclature__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG22(association.transaction).validate(association)


def test_NIG23(date_ranges):
    """The period of the association with a footnote must be within the validity
    period of the footnote."""
    association = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG23(association.transaction).validate(association)


@pytest.mark.xfail(reason="NIG24 disabled")
@pytest.mark.parametrize(
    "valid_between, expect_error",
    [
        ("overlap_normal", True),
        ("adjacent_later", False),
    ],
)
def test_NIG24(date_ranges, valid_between, expect_error):
    """When the same footnote is associated more than once with the same
    nomenclature then there may be no overlap in their association periods."""

    existing = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
    )
    association = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=existing.associated_footnote,
        goods_nomenclature=existing.goods_nomenclature,
        valid_between=getattr(date_ranges, valid_between),
    )

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.NIG24(association.transaction).validate(association)


def test_NIG30(assert_spanning_enforced):
    """When a goods nomenclature is used in a goods measure then the validity
    period of the goods nomenclature must span the validity period of the goods
    measure."""
    assert_spanning_enforced(
        factories.GoodsNomenclatureFactory,
        business_rules.NIG30,
        measures=factories.related_factory(
            factories.MeasureFactory,
            factory_related_name="goods_nomenclature",
        ),
    )


def test_NIG31(assert_spanning_enforced):
    """When a goods nomenclature is used in an additional nomenclature measure
    then the validity period of the goods nomenclature must span the validity
    period of the additional nomenclature measure."""
    assert_spanning_enforced(
        factories.GoodsNomenclatureFactory,
        business_rules.NIG31,
        measures=factories.related_factory(
            factories.MeasureWithAdditionalCodeFactory,
            factory_related_name="goods_nomenclature",
        ),
    )


def test_NIG34(delete_record):
    """A goods nomenclature cannot be deleted if it is used in a goods
    measure."""

    measure = factories.MeasureFactory.create()
    deleted_record = delete_record(measure.goods_nomenclature)
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG34(deleted_record.transaction).validate(deleted_record)


def test_NIG35(delete_record):
    """A goods nomenclature cannot be deleted if it is used in an additional
    nomenclature measure."""

    measure = factories.MeasureWithAdditionalCodeFactory.create()
    deleted_record = delete_record(measure.goods_nomenclature)
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG35(deleted_record.transaction).validate(deleted_record)


@pytest.mark.skip(reason="Not using export refunds")
def test_NIG36():
    """A goods nomenclature cannot be deleted if it is used in an Export refund
    nomenclature."""
    assert False
