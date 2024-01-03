import pytest

from commodities import business_rules
from commodities.models import GoodsNomenclatureOrigin
from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


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


def test_NIG5_allow_origin_create():
    """
    When creating a goods nomenclature code, an origin must exist.

    This rule is only applicable to update extractions.
    """

    # create published workbasket with goods nomenclature without origin
    published_workbasket = factories.PublishedWorkBasketFactory()

    approved_transaction = factories.ApprovedTransactionFactory.create(
        workbasket=published_workbasket,
        order=1,
    )

    approved_transaction_2 = factories.ApprovedTransactionFactory.create(
        workbasket=published_workbasket,
        order=2,
    )

    old_good_no_origin = factories.GoodsNomenclatureFactory.create(
        item_id="2000000010",
        origin=None,
        indent__indent=1,
        update_type=UpdateType.CREATE,
        transaction_id=approved_transaction.id,
    )

    old_goods_should_be_origin_for_above = factories.GoodsNomenclatureFactory.create(
        item_id="2000000000",
        update_type=UpdateType.CREATE,
        transaction_id=approved_transaction_2.id,
    )

    # create edit workbasket with correction to add in origin
    editable_workbasket = factories.WorkBasketFactory()

    editable_transaction = factories.TransactionFactory.create(
        workbasket=editable_workbasket,
        order=3,
    )

    new_origin = GoodsNomenclatureOrigin.objects.create(
        transaction=editable_transaction,
        derived_from_goods_nomenclature=old_good_no_origin,
        update_type=UpdateType.CREATE,
        new_goods_nomenclature=old_goods_should_be_origin_for_above,
    )

    business_rules.NIG5(new_origin.transaction).validate(
        old_goods_should_be_origin_for_above,
    )
