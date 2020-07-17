import pytest
from django.core.exceptions import ValidationError
from django.db import DataError
from django.db import IntegrityError

from common.tests import factories
from common.tests.util import requires_measures


pytestmark = pytest.mark.django_db


def generate_good(
    valid_between, workbasket=None, indent_kwargs=None, with_description=True, **kwargs
):
    if not workbasket:
        workbasket = factories.WorkBasketFactory()
    kwargs["workbasket"] = workbasket
    goods_kwargs = {
        f"indented_goods_nomenclature__{key}": value for key, value in kwargs.items()
    }

    good = factories.GoodsNomenclatureIndentFactory(
        indented_goods_nomenclature__valid_between=valid_between,
        workbasket=workbasket,
        valid_between=valid_between,
        **indent_kwargs or {},
        **goods_kwargs,
    ).indented_goods_nomenclature

    if with_description:
        factories.GoodsNomenclatureDescriptionFactory(
            described_goods_nomenclature=good,
            workbasket=workbasket,
            valid_between=valid_between,
        )

    return good


@pytest.fixture
def normal_good(date_ranges):
    return generate_good(date_ranges.normal)


def test_NIG1(date_ranges, normal_good):
    """
    The validity period of the goods nomenclature must not overlap any other goods nomenclature with the
    same SID.
    """
    with pytest.raises(IntegrityError):
        generate_good(sid=normal_good.sid, valid_between=date_ranges.overlap_normal)


def test_NIG2(date_ranges, normal_good):
    """
    The validity period of the goods nomenclature must be within the validity period
    of the product line above in the hierarchy.

    Also covers NIG3
    """
    parent = factories.GoodsNomenclatureIndentFactory(valid_between=date_ranges.big)
    generate_good(
        origin=normal_good, valid_between=date_ranges.adjacent_later,
    )
    with pytest.raises(ValidationError):
        generate_good(
            valid_between=date_ranges.adjacent_later_big,
            origin=normal_good,
            indent_kwargs={"parent": parent},
        )


def test_NIG4(date_ranges):
    """
    The start date of the goods nomenclature must be less than or equal to the end date.
    """
    with pytest.raises(DataError):
        generate_good(valid_between=date_ranges.backwards)


def test_NIG5(date_ranges):
    """
    When creating a goods nomenclature code, an origin must exist. This rule is only applicable to update extractions.
    """
    origin = generate_good(valid_between=date_ranges.normal)
    parent = factories.GoodsNomenclatureIndentFactory(valid_between=date_ranges.big)

    with pytest.raises(ValidationError):
        good = generate_good(
            valid_between=date_ranges.adjacent_later, indent_kwargs={"parent": parent}
        )
        good.workbasket.submit_for_approval()

    good = generate_good(
        origin=origin,
        valid_between=date_ranges.adjacent_later,
        indent_kwargs={"parent": parent},
    )
    good.workbasket.submit_for_approval()


def test_NIG7(date_ranges):
    """
    The origin must be applicable the day before the start date of the new code entered.

    This covers NIG10 as well
    """

    origin = generate_good(valid_between=date_ranges.normal)
    with pytest.raises(ValidationError):
        generate_good(origin=origin, valid_between=date_ranges.later)
    with pytest.raises(ValidationError):
        generate_good(origin=origin, valid_between=date_ranges.earlier)
    with pytest.raises(ValidationError):
        generate_good(origin=origin, valid_between=date_ranges.adjacent_earlier)
    with pytest.raises(ValidationError):
        generate_good(origin=origin, valid_between=date_ranges.overlap_normal)

    generate_good(origin=origin, valid_between=date_ranges.adjacent_later)


def test_NIG11_one_indent_mandatory(date_ranges):
    """
    At least one indent record is mandatory. The start date of the first indentation must
    be equal to the start date of the nomenclature.
    """
    workbasket = factories.WorkBasketFactory()
    good = factories.GoodsNomenclatureDescriptionFactory(
        workbasket=workbasket, described_goods_nomenclature__workbasket=workbasket
    ).described_goods_nomenclature

    with pytest.raises(ValidationError):
        workbasket.submit_for_approval()

    factories.GoodsNomenclatureIndentFactory(
        workbasket=workbasket, indented_goods_nomenclature=good
    )

    workbasket.submit_for_approval()


def test_NIG11_no_overlapping_indents(date_ranges):
    """
    No two associated indentations may have the same start date.
    """
    indent = factories.GoodsNomenclatureIndentFactory(valid_between=date_ranges.normal)
    with pytest.raises(IntegrityError):
        factories.GoodsNomenclatureIndentFactory(
            sid=indent.sid, valid_between=date_ranges.overlap_normal
        )


def test_NIG11_start_date_less_than_end_date(date_ranges):
    """
    The start date must be less than or equal to the end date
    of the nomenclature
    """
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureIndentFactory(
            indented_goods_nomenclature__valid_between=date_ranges.normal,
            valid_between=date_ranges.later,
        )


def test_NIG12(date_ranges):
    """
    At least one description is mandatory. The start date of the first description period
    must be equal to the start date of the nomenclature.
    """
    good = generate_good(valid_between=date_ranges.normal, with_description=False)

    with pytest.raises(ValidationError):
        good.workbasket.submit_for_approval()

    description = factories.GoodsNomenclatureDescriptionFactory(
        described_goods_nomenclature=good,
        workbasket=good.workbasket,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(ValidationError):
        good.workbasket.submit_for_approval()

    description.valid_between = date_ranges.normal
    description.save()

    good.workbasket.submit_for_approval()


def test_NIG21(date_ranges):
    """
    The start date of the association with a footnote must be less than or equal to the end date of the association.
    """
    with pytest.raises(DataError):
        factories.FootnoteAssociationGoodsNomenclatureFactory(
            valid_between=date_ranges.backwards
        )


def test_NIG22(date_ranges):
    """
    The period of the association with a footnote must be within the validity period of the nomenclature.
    """
    good = factories.GoodsNomenclatureFactory(valid_between=date_ranges.big)
    factories.FootnoteAssociationGoodsNomenclatureFactory(
        goods_nomenclature=good, valid_between=date_ranges.normal
    )
    with pytest.raises(ValidationError):
        factories.FootnoteAssociationGoodsNomenclatureFactory(
            goods_nomenclature=good, valid_between=date_ranges.overlap_big
        )


def test_NIG23(date_ranges):
    """
    The period of the association with a footnote must be within the validity period of the footnote.
    """
    footnote = factories.FootnoteFactory(
        footnote_type__valid_between=date_ranges.big, valid_between=date_ranges.normal
    )
    factories.FootnoteAssociationGoodsNomenclatureFactory(
        associated_footnote=footnote, valid_between=date_ranges.starts_with_normal
    )
    with pytest.raises(ValidationError):
        factories.FootnoteAssociationGoodsNomenclatureFactory(
            associated_footnote=footnote, valid_between=date_ranges.later
        )


def test_NIG24(date_ranges):
    """
    When the same footnote is associated more than once with the same nomenclature then
    there may be no overlap in their association periods.
    """
    association = factories.FootnoteAssociationGoodsNomenclatureFactory(
        valid_between=date_ranges.normal
    )
    with pytest.raises(ValidationError):
        factories.FootnoteAssociationGoodsNomenclatureFactory(
            associated_footnote=association.associated_footnote,
            goods_nomenclature=association.goods_nomenclature,
            valid_between=date_ranges.overlap_normal,
        )
    factories.FootnoteAssociationGoodsNomenclatureFactory(
        associated_footnote=association.associated_footnote,
        goods_nomenclature=association.goods_nomenclature,
        valid_between=date_ranges.adjacent_later,
    )


@requires_measures
def test_NIG30():
    """
    When a goods nomenclature is used in a goods measure then the validity period of the goods
    nomenclature must span the validity period of the goods measure.
    """
    pass


@requires_measures
def test_NIG31():
    """
    When a goods nomenclature is used in an additional nomenclature measure then the validity
    period of the goods nomenclature must span the validity period of the additional
    nomenclature measure.
    """
    pass


@requires_measures
def test_NIG34():
    """
    A goods nomenclature cannot be deleted if it is used in a goods measure.
    """
    pass


@requires_measures
def test_NIG35():
    """
    A goods nomenclature cannot be deleted if it is used in an additional nomenclature measure.
    """
    pass


@requires_measures
def test_NIG36():
    """
    A goods nomenclature cannot be deleted if it is used in an Export refund nomenclature.
    """
    pass
