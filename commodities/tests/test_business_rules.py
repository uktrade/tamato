import pytest
from django.core.exceptions import ValidationError
from django.db import DataError
from django.db import IntegrityError

from common.tests import factories


pytestmark = pytest.mark.django_db


def test_NIG1(date_ranges, normal_good):
    """
    The validity period of the goods nomenclature must not overlap any other goods nomenclature with the
    same SID.
    """

    good = factories.GoodsNomenclatureFactory.create()
    with pytest.raises(IntegrityError):
        factories.GoodsNomenclatureFactory.create(
            sid=good.sid, valid_between=good.valid_between
        )


def test_NIG2(date_ranges, normal_good):
    """
    The validity period of the goods nomenclature must be within the validity period
    of the product line above in the hierarchy.

    Also covers NIG3
    """
    parent = factories.GoodsNomenclatureIndentFactory.create(
        valid_between=date_ranges.big,
        indented_goods_nomenclature__valid_between=date_ranges.big,
    ).nodes.first()
    factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.adjacent_later,
    )
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureFactory.create(
            valid_between=date_ranges.adjacent_later_big,
            indent__node__parent=parent,
        )


def test_NIG4(date_ranges):
    """
    The start date of the goods nomenclature must be less than or equal to the end date.
    """
    with pytest.raises(DataError):
        factories.GoodsNomenclatureFactory.create(valid_between=date_ranges.backwards)


def test_NIG5(date_ranges, unapproved_workbasket):
    """
    When creating a goods nomenclature code, an origin must exist. This rule is only applicable to update extractions.
    """
    origin = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
    )
    parent = factories.GoodsNomenclatureIndentFactory.create(
        valid_between=date_ranges.big
    ).nodes.first()

    with pytest.raises(ValidationError):
        good = factories.GoodsNomenclatureFactory.create(
            origin=None,
            valid_between=date_ranges.adjacent_later,
            indent__node__parent=parent,
            workbasket=unapproved_workbasket,
        )
        good.workbasket.submit_for_approval()

    good = factories.GoodsNomenclatureFactory.create(
        origin__derived_from_goods_nomenclature=origin,
        valid_between=date_ranges.adjacent_later,
        indent__node__parent=parent,
        workbasket=factories.WorkBasketFactory.create(),
    )
    good.workbasket.submit_for_approval()


def test_NIG7(date_ranges):
    """
    The origin must be applicable the day before the start date of the new code entered.
    """

    origin = factories.GoodsNomenclatureFactory.create(valid_between=date_ranges.normal)
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureFactory.create(
            origin__derived_from_goods_nomenclature=origin,
            valid_between=date_ranges.later,
        )
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureFactory.create(
            origin__derived_from_goods_nomenclature=origin,
            valid_between=date_ranges.earlier,
        )
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureFactory.create(
            origin__derived_from_goods_nomenclature=origin,
            valid_between=date_ranges.adjacent_earlier,
        )
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureFactory.create(
            origin__derived_from_goods_nomenclature=origin,
            valid_between=date_ranges.normal,
        )

    factories.GoodsNomenclatureFactory.create(
        origin__derived_from_goods_nomenclature=origin,
        valid_between=date_ranges.overlap_normal,
    )
    factories.GoodsNomenclatureFactory.create(
        origin__derived_from_goods_nomenclature=origin,
        valid_between=date_ranges.adjacent_later,
    )


def test_NIG10(date_ranges):
    """
    The successor must be applicable the day after the end date of the old code.
    """

    successor = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal
    )
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureWithSuccessorFactory.create(
            successor__absorbed_into_goods_nomenclature=successor,
            valid_between=date_ranges.later,
        )
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureWithSuccessorFactory.create(
            successor__absorbed_into_goods_nomenclature=successor,
            valid_between=date_ranges.earlier,
        )
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureWithSuccessorFactory.create(
            successor__absorbed_into_goods_nomenclature=successor,
            valid_between=date_ranges.no_end,
        )

    factories.GoodsNomenclatureWithSuccessorFactory.create(
        successor__absorbed_into_goods_nomenclature=successor,
        valid_between=date_ranges.adjacent_earlier,
    )
    factories.GoodsNomenclatureWithSuccessorFactory.create(
        successor__absorbed_into_goods_nomenclature=successor,
        valid_between=date_ranges.overlap_normal_earlier,
    )


def test_NIG11_one_indent_mandatory(date_ranges):
    """
    At least one indent record is mandatory. The start date of the first indentation must
    be equal to the start date of the nomenclature.
    """
    workbasket = factories.WorkBasketFactory.create()
    good = factories.GoodsNomenclatureDescriptionFactory.create(
        workbasket=workbasket,
        described_goods_nomenclature__workbasket=workbasket,
        described_goods_nomenclature__indent=None,
        described_goods_nomenclature__description=None,
    ).described_goods_nomenclature

    with pytest.raises(ValidationError):
        workbasket.submit_for_approval()

    factories.GoodsNomenclatureIndentFactory.create(
        workbasket=workbasket, indented_goods_nomenclature=good
    )

    workbasket.submit_for_approval()


def test_NIG11_no_overlapping_indents(date_ranges):
    """
    No two associated indentations may have the same start date.
    """
    indent = factories.GoodsNomenclatureIndentFactory.create(
        valid_between=date_ranges.normal
    )

    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureIndentFactory.create(
            sid=indent.sid, valid_between=date_ranges.normal
        )


def test_NIG11_start_date_less_than_end_date(date_ranges):
    """
    The start date must be less than or equal to the end date
    of the nomenclature
    """
    with pytest.raises(ValidationError):
        factories.GoodsNomenclatureIndentFactory.create(
            indented_goods_nomenclature__valid_between=date_ranges.normal,
            valid_between=date_ranges.later,
        )


def test_NIG12(date_ranges, unapproved_workbasket):
    """
    At least one description is mandatory. The start date of the first description period
    must be equal to the start date of the nomenclature.
    """
    good = factories.GoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal,
        description=None,
        workbasket=unapproved_workbasket,
    )

    with pytest.raises(ValidationError):
        good.workbasket.submit_for_approval()

    description = factories.GoodsNomenclatureDescriptionFactory.create(
        described_goods_nomenclature=good,
        workbasket=unapproved_workbasket,
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
        factories.FootnoteAssociationGoodsNomenclatureFactory.create(
            valid_between=date_ranges.backwards
        )


def test_NIG22(date_ranges):
    """
    The period of the association with a footnote must be within the validity period of the nomenclature.
    """
    good = factories.GoodsNomenclatureFactory.create(
        origin__derived_from_goods_nomenclature__valid_between=date_ranges.adjacent_earlier_big,
        valid_between=date_ranges.big,
    )
    factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        goods_nomenclature=good, valid_between=date_ranges.normal
    )
    with pytest.raises(ValidationError):
        factories.FootnoteAssociationGoodsNomenclatureFactory.create(
            goods_nomenclature=good, valid_between=date_ranges.overlap_big
        )


def test_NIG23(date_ranges):
    """
    The period of the association with a footnote must be within the validity period of the footnote.
    """
    footnote = factories.FootnoteFactory.create(
        footnote_type__valid_between=date_ranges.big, valid_between=date_ranges.normal
    )
    factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=footnote, valid_between=date_ranges.starts_with_normal
    )
    with pytest.raises(ValidationError):
        factories.FootnoteAssociationGoodsNomenclatureFactory.create(
            associated_footnote=footnote, valid_between=date_ranges.later
        )


def test_NIG24(date_ranges):
    """
    When the same footnote is associated more than once with the same nomenclature then
    there may be no overlap in their association periods.
    """
    association = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        valid_between=date_ranges.normal
    )
    with pytest.raises(ValidationError):
        factories.FootnoteAssociationGoodsNomenclatureFactory.create(
            associated_footnote=association.associated_footnote,
            goods_nomenclature=association.goods_nomenclature,
            valid_between=date_ranges.overlap_normal,
        )
    factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=association.associated_footnote,
        goods_nomenclature=association.goods_nomenclature,
        valid_between=date_ranges.adjacent_later,
    )


def test_NIG30(validity_period_contained):
    """
    When a goods nomenclature is used in a goods measure then the validity period of the goods
    nomenclature must span the validity period of the goods measure.
    """

    assert validity_period_contained(
        "goods_nomenclature",
        factories.GoodsNomenclatureFactory,
        factories.MeasureFactory,
    )


@pytest.mark.skip(reason="Needs clarification")
def test_NIG31():
    """
    When a goods nomenclature is used in an additional nomenclature measure then the validity
    period of the goods nomenclature must span the validity period of the additional
    nomenclature measure.
    """
    assert False


def test_NIG34(approved_workbasket):
    """
    A goods nomenclature cannot be deleted if it is used in a goods measure.
    """

    measure = factories.MeasureFactory.create(
        goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            workbasket=approved_workbasket,
        ),
        workbasket=approved_workbasket,
    )

    with pytest.raises(IntegrityError):
        measure.goods_nomenclature.delete()


@pytest.mark.skip(reason="Needs clarification")
def test_NIG35():
    """
    A goods nomenclature cannot be deleted if it is used in an additional nomenclature measure.
    """
    assert False


@pytest.mark.skip(reason="Not using export refunds")
def test_NIG36():
    """
    A goods nomenclature cannot be deleted if it is used in an Export refund nomenclature.
    """
    assert False
