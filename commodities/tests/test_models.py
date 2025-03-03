import pytest

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


def test_goods_nomenclature_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.GoodsNomenclatureFactory,
        "in_use",
        factories.MeasureFactory,
        "goods_nomenclature",
    )


@pytest.mark.parametrize(
    "factory",
    [
        factories.GoodsNomenclatureFactory,
        factories.GoodsNomenclatureIndentFactory,
        factories.GoodsNomenclatureDescriptionFactory,
        factories.GoodsNomenclatureOriginFactory,
        factories.GoodsNomenclatureSuccessorFactory,
        factories.FootnoteAssociationGoodsNomenclatureFactory,
    ],
)
def test_commodities_update_types(factory, check_update_validation):
    assert check_update_validation(factory)


def test_current_version_inc_draft(user_workbasket):
    """Test the current version including draft property correctly returns."""
    commodity = factories.GoodsNomenclatureFactory.create()
    with override_current_transaction(Transaction.objects.last()):
        assert commodity.current_version_inc_draft == commodity

    updated_commodity = commodity.new_version(workbasket=user_workbasket)
    with override_current_transaction(Transaction.objects.last()):
        assert commodity.current_version_inc_draft == updated_commodity

    deleted_commodity = commodity.new_version(
        workbasket=user_workbasket,
        update_type=UpdateType.DELETE,
    )
    with override_current_transaction(Transaction.objects.last()):
        assert commodity.current_version_inc_draft == None
