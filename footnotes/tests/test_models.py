import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_footnote_type_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.FootnoteTypeFactory,
        "in_use",
        factories.FootnoteFactory,
        "footnote_type",
    )


def test_footnote_used_in_additional_code(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.FootnoteFactory,
        "used_in_additional_code",
        factories.FootnoteAssociationAdditionalCodeFactory,
        "associated_footnote",
    )


def test_footnote_used_in_goods_nomenclature(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.FootnoteFactory,
        "used_in_goods_nomenclature",
        factories.FootnoteAssociationGoodsNomenclatureFactory,
        "associated_footnote",
    )


def test_footnote_used_in_measure(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.FootnoteFactory,
        "used_in_measure",
        factories.FootnoteAssociationMeasureFactory,
        "associated_footnote",
    )
