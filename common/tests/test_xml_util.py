import pytest
from django.db import transaction

from common.models.transactions import Transaction
from common.tests import factories
from common.tests.util import serialize_xml
from common.xml.util import remove_transactions
from common.xml.util import renumber_records
from common.xml.util import renumber_transactions

pytestmark = pytest.mark.django_db


def test_record_renumbering_produces_valid_import_data(import_xml, export_xml):
    """Tests that when the renumbering function is used, the XML file it
    produces is valid and when imported produces records in the database that
    are correctly renumbered."""
    code_type = factories.AdditionalCodeTypeFactory.create()
    workbasket = factories.ApprovedWorkBasketFactory()
    first = factories.AdditionalCodeFactory.create(
        type=code_type,
        transaction__workbasket=workbasket,
    )
    second = factories.AdditionalCodeFactory.create(
        type=code_type,
        transaction__workbasket=workbasket,
    )

    for instance in (first, second):
        assert not type(instance).objects.filter(sid=instance.sid + 2).exists()

    xml = export_xml(workbasket=workbasket)
    renumber_records(xml, second.sid + 1, "oub:additional.code.sid")
    import_xml(serialize_xml(xml))

    for instance in (first, second):
        new_instance = type(instance).objects.get(sid=instance.sid + 2)
        assert new_instance.type == instance.type
        assert new_instance.code == instance.code
        assert new_instance.version_group != instance.version_group


def test_transaction_renumbering_produces_valid_import_data(import_xml, export_xml):
    """Tests that when the transaction renumbering function is used, the XML
    file it produces is valid and when imported produces transactions in the
    database that are correctly renumbered."""
    with transaction.atomic():
        model = factories.AdditionalCodeTypeFactory.create()
        xml = export_xml(workbasket=model.transaction.workbasket)
        original_order = model.transaction.order
        transaction.set_rollback(True)

    assert not Transaction.objects.filter(order=original_order).exists()
    assert not Transaction.objects.filter(order=original_order + 1).exists()
    renumber_transactions(xml, original_order + 1)
    import_xml(serialize_xml(xml))

    txn = Transaction.objects.get(order=original_order + 1)
    assert txn.tracked_models.get().sid == model.sid


def test_transaction_removing_produces_valid_import_data(import_xml, export_xml):
    """Tests that when the transaction filtering function is used, the XML file
    it produces is valid and when imported does not contain the removed
    transactions."""
    code_type = factories.AdditionalCodeTypeFactory.create()
    with transaction.atomic():
        workbasket = factories.ApprovedWorkBasketFactory()
        first = factories.AdditionalCodeFactory.create(
            type=code_type,
            transaction__workbasket=workbasket,
        )
        second = factories.AdditionalCodeFactory.create(
            type=code_type,
            transaction__workbasket=workbasket,
        )
        xml = export_xml(workbasket=workbasket)
        transaction.set_rollback(True)

    assert not Transaction.objects.filter(order=first.transaction.order).exists()
    assert not Transaction.objects.filter(order=second.transaction.order).exists()

    remove_transactions(xml, "oub:additional.code.sid", [str(first.sid)])
    import_xml(serialize_xml(xml))

    assert not Transaction.objects.filter(order=first.transaction.order).exists()
    assert Transaction.objects.filter(order=second.transaction.order).exists()
    assert not type(first).objects.filter(sid=first.sid).exists()
    assert type(second).objects.filter(sid=second.sid).exists()
