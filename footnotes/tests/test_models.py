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
        "in_use",
        factories.FootnoteAssociationAdditionalCodeFactory,
        "associated_footnote",
    )


def test_footnote_used_in_goods_nomenclature(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.FootnoteFactory,
        "in_use",
        factories.FootnoteAssociationGoodsNomenclatureFactory,
        "associated_footnote",
    )


def test_footnote_used_in_measure(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.FootnoteFactory,
        "in_use",
        factories.FootnoteAssociationMeasureFactory,
        "associated_footnote",
    )


@pytest.mark.parametrize(
    "factory",
    [
        factories.FootnoteTypeFactory,
        factories.FootnoteFactory,
        factories.FootnoteDescriptionFactory,
    ],
)
def test_footnote_update_types(factory, check_update_validation):
    assert check_update_validation(factory)
