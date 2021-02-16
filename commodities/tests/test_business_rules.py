import pytest
from django.db import DataError

from commodities import business_rules
from common.business_rules import BusinessRuleViolation
from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.xfail(reason="NIG1 disabled")
def test_NIG1():
    """The validity period of the goods nomenclature must not overlap any other
    goods nomenclature with the same SID."""

    good = factories.GoodsNomenclatureFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG1().validate(
            factories.GoodsNomenclatureFactory.create(
                sid=good.sid,
                valid_between=good.valid_between,
            ),
        )


def test_NIG2(date_ranges):
    """
    The validity period of the goods nomenclature must be within the validity
    period of the product line above in the hierarchy.

    Also covers NIG3
    """

    parent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=date_ranges.big,
    )
    child = factories.GoodsNomenclatureIndentFactory.create(
        node__parent=parent.nodes.first(),
        indented_goods_nomenclature__valid_between=date_ranges.adjacent_later_big,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG2().validate(child)


def test_NIG4(date_ranges):
    """The start date of the goods nomenclature must be less than or equal to
    the end date."""

    with pytest.raises(DataError):
        factories.GoodsNomenclatureFactory.create(valid_between=date_ranges.backwards)


def test_NIG5():
    """
    When creating a goods nomenclature code, an origin must exist.

    This rule is only applicable to update extractions.
    """

    origin = factories.GoodsNomenclatureFactory.create()
    parent_node = factories.GoodsNomenclatureIndentFactory.create().nodes.first()

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG5().validate(
            factories.GoodsNomenclatureFactory.create(
                origin=None,
                indent__node__parent=parent_node,
            ),
        )

    business_rules.NIG5().validate(
        factories.GoodsNomenclatureFactory.create(
            origin__derived_from_goods_nomenclature=origin,
            indent__node__parent=parent_node,
        ),
    )


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

    try:
        business_rules.NIG7().validate(
            factories.GoodsNomenclatureOriginFactory.create(
                derived_from_goods_nomenclature__valid_between=date_ranges.normal,
                new_goods_nomenclature__valid_between=getattr(
                    date_ranges,
                    valid_between,
                ),
            ),
        )
    except BusinessRuleViolation:
        if not expect_error:
            raise
    else:
        if expect_error:
            pytest.fail("DID NOT RAISE BusinessRuleViolation")


@pytest.mark.parametrize(
    "valid_between, expect_error",
    [
        ("later", True),
        ("earlier", True),
        ("no_end", True),
        ("adjacent_earlier", False),
        ("overlap_normal_earlier", False),
    ],
)
def test_NIG10(date_ranges, valid_between, expect_error):
    """The successor must be applicable the day after the end date of the old
    code."""

    try:
        business_rules.NIG10().validate(
            factories.GoodsNomenclatureSuccessorFactory.create(
                absorbed_into_goods_nomenclature__valid_between=date_ranges.normal,
                replaced_goods_nomenclature__valid_between=getattr(
                    date_ranges,
                    valid_between,
                ),
            ),
        )
    except BusinessRuleViolation:
        if not expect_error:
            raise
    else:
        if expect_error:
            pytest.fail("DID NOT RAISE BusinessRuleViolation")


def test_NIG11_one_indent_mandatory():
    """At least one indent record is mandatory."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11().validate(
            factories.GoodsNomenclatureFactory.create(indent=None),
        )


def test_NIG11_first_indent_must_have_same_start_date(date_ranges):
    """The start date of the first indentation must be equal to the start date
    of the nomenclature."""

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11().validate(indent.indented_goods_nomenclature)


def test_NIG11_no_overlapping_indents():
    """No two associated indentations may have the same start date."""

    existing = factories.GoodsNomenclatureIndentFactory.create()
    factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=existing.indented_goods_nomenclature,
        valid_between=existing.valid_between,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11().validate(existing.indented_goods_nomenclature)


def test_NIG11_start_date_less_than_end_date(date_ranges):
    """The start date must be less than or equal to the end date of the
    nomenclature."""

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=date_ranges.normal,
        valid_between=date_ranges.later,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11().validate(indent.indented_goods_nomenclature)


def test_NIG12_one_description_mandatory():
    """At least one description record is mandatory."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG12().validate(
            factories.GoodsNomenclatureFactory.create(description=None),
        )


def test_NIG12_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start
    date of the nomenclature."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG12().validate(
            factories.GoodsNomenclatureFactory.create(
                description__valid_between=date_ranges.later,
            ),
        )


def test_NIG12_start_dates_cannot_match():
    """No two associated description periods may have the same start date."""

    goods_nomenclature = factories.GoodsNomenclatureFactory.create()
    factories.GoodsNomenclatureDescriptionFactory.create(
        described_goods_nomenclature=goods_nomenclature,
        valid_between=goods_nomenclature.valid_between,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG12().validate(goods_nomenclature)


def test_NIG12_description_start_before_nomenclature_end(
    date_ranges,
    unapproved_transaction,
):
    """The start date must be less than or equal to the end date of the
    nomenclature."""

    goods_nomenclature = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
        description__valid_between=date_ranges.starts_with_normal,
        transaction=unapproved_transaction,
    )
    factories.GoodsNomenclatureDescriptionFactory.create(
        described_goods_nomenclature=goods_nomenclature,
        valid_between=date_ranges.later,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG12().validate(goods_nomenclature)


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

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG22().validate(
            factories.FootnoteAssociationGoodsNomenclatureFactory.create(
                goods_nomenclature__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_NIG23(date_ranges):
    """The period of the association with a footnote must be within the validity
    period of the footnote."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG23().validate(
            factories.FootnoteAssociationGoodsNomenclatureFactory.create(
                associated_footnote__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            ),
        )


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

    try:
        business_rules.NIG24().validate(
            factories.FootnoteAssociationGoodsNomenclatureFactory.create(
                associated_footnote=existing.associated_footnote,
                goods_nomenclature=existing.goods_nomenclature,
                valid_between=getattr(date_ranges, valid_between),
            ),
        )
    except BusinessRuleViolation:
        if not expect_error:
            raise
    else:
        if expect_error:
            pytest.fail("DID NOT RAISE BusinessRuleViolation")


def test_NIG30(date_ranges):
    """When a goods nomenclature is used in a goods measure then the validity
    period of the goods nomenclature must span the validity period of the goods
    measure."""

    measure = factories.MeasureFactory.create(
        goods_nomenclature__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG30().validate(measure.goods_nomenclature)


def test_NIG31(date_ranges):
    """When a goods nomenclature is used in an additional nomenclature measure
    then the validity period of the goods nomenclature must span the validity
    period of the additional nomenclature measure."""

    measure = factories.MeasureWithAdditionalCodeFactory.create(
        additional_code__valid_between=date_ranges.overlap_normal,
        goods_nomenclature__valid_between=date_ranges.normal,
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG31().validate(measure.goods_nomenclature)


def test_NIG34(delete_record):
    """A goods nomenclature cannot be deleted if it is used in a goods
    measure."""

    measure = factories.MeasureFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG34().validate(delete_record(measure.goods_nomenclature))


def test_NIG35(delete_record):
    """A goods nomenclature cannot be deleted if it is used in an additional
    nomenclature measure."""

    measure = factories.MeasureWithAdditionalCodeFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG35().validate(delete_record(measure.goods_nomenclature))


@pytest.mark.skip(reason="Not using export refunds")
def test_NIG36():
    """A goods nomenclature cannot be deleted if it is used in an Export refund
    nomenclature."""
    assert False
