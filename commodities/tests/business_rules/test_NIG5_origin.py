import pytest

from commodities import business_rules
from commodities.models import GoodsNomenclatureOrigin
from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


def test_NIG5_origin_raises_violation_when_only_origin_is_deleted(workbasket):
    """
    When deleting an origin there must still be an origin for the goods,
    provided the goods is not also being deleted in the same transaction.

    This rule is only applicable when origins are deleted.
    """
    # Setup data
    published_workbasket = factories.PublishedWorkBasketFactory()

    approved_transaction = factories.ApprovedTransactionFactory.create(
        workbasket=published_workbasket,
        order=1,
    )

    approved_transaction_2 = factories.ApprovedTransactionFactory.create(
        workbasket=published_workbasket,
        order=2,
    )

    goods_chapter = factories.GoodsNomenclatureFactory.create(
        item_id="2000000000",
        transaction=approved_transaction,
    )

    # This is the goods we are going to delete the origin from
    goods = factories.GoodsNomenclatureFactory.create(
        item_id="2000000010",
        origin__derived_from_goods_nomenclature=goods_chapter,
        indent__indent=1,
        transaction=approved_transaction_2,
    )

    editable_workbasket = factories.WorkBasketFactory()

    editable_transaction = factories.TransactionFactory.create(
        workbasket=editable_workbasket,
        order=3,
    )

    origin_delete = (
        GoodsNomenclatureOrigin.objects.approved_up_to_transaction(
            approved_transaction_2,
        )
        .get(
            new_goods_nomenclature=goods,
            derived_from_goods_nomenclature=goods_chapter,
        )
        .new_version(
            transaction=editable_transaction,
            update_type=UpdateType.DELETE,
            workbasket=editable_workbasket,
        )
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG5_origin(editable_transaction).validate(origin_delete)


def test_NIG5_origin_does_not_raise_violation_when_origin_still_exists(workbasket):
    """
    When deleting an origin there must still be an origin for the goods,
    provided the goods is not also being deleted in the same transaction.

    This rule is only applicable when origins are deleted.
    """
    # Setup data
    published_workbasket = factories.PublishedWorkBasketFactory()

    approved_transaction = factories.ApprovedTransactionFactory.create(
        workbasket=published_workbasket,
        order=1,
    )

    approved_transaction_2 = factories.ApprovedTransactionFactory.create(
        workbasket=published_workbasket,
        order=2,
    )

    approved_transaction_3 = factories.ApprovedTransactionFactory.create(
        workbasket=published_workbasket,
        order=3,
    )

    goods_chapter = factories.GoodsNomenclatureFactory.create(
        item_id="2000000000",
        transaction=approved_transaction,
    )

    # This is the goods we are going to delete the origin from
    goods = factories.GoodsNomenclatureFactory.create(
        item_id="2000000010",
        origin__derived_from_goods_nomenclature=goods_chapter,
        indent__indent=1,
        transaction=approved_transaction_2,
    )

    # create a second origin
    GoodsNomenclatureOrigin.objects.create(
        derived_from_goods_nomenclature=goods_chapter,
        new_goods_nomenclature=goods,
        update_type=UpdateType.CREATE,
        transaction=approved_transaction_3,
    )

    editable_workbasket = factories.WorkBasketFactory()

    editable_transaction = factories.TransactionFactory.create(
        workbasket=editable_workbasket,
        order=4,
    )

    origin_delete = (
        GoodsNomenclatureOrigin.objects.approved_up_to_transaction(
            approved_transaction_2,
        )
        .filter(
            new_goods_nomenclature=goods,
            derived_from_goods_nomenclature=goods_chapter,
        )
        .first()
        .new_version(
            transaction=editable_transaction,
            update_type=UpdateType.DELETE,
            workbasket=editable_workbasket,
        )
    )

    business_rules.NIG5_origin(editable_transaction).validate(origin_delete)
