from unittest.mock import patch

import pytest
from lxml import etree

from common.tests import factories
from exporter.management.commands import util

pytestmark = pytest.mark.django_db


def test_dump_transactions_success(tmp_path, capsys, approved_transaction):
    factories.GoodsNomenclatureFactory.create(transaction=approved_transaction)
    transactions = approved_transaction.workbasket.transactions.all()
    envelope_id = 123
    directory = tmp_path / "test_directory"
    directory.mkdir()
    util.dump_transactions(transactions, envelope_id, directory, None)
    output = capsys.readouterr().out
    path = directory.__str__()
    total_transactions = approved_transaction.workbasket.transactions.count()

    assert (
        f"{path}/DIT000123.xml \N{WHITE HEAVY CHECK MARK} XML valid. {total_transactions} transactions, serialized"
        in output
    )


def test_dump_transactions_empty(tmp_path, capsys, approved_transaction):
    transactions = approved_transaction.workbasket.transactions.all()
    envelope_id = 123
    directory = tmp_path / "test_directory"
    directory.mkdir()
    util.dump_transactions(transactions, envelope_id, directory, None)
    output = capsys.readouterr().out
    path = directory.__str__()

    assert (
        f"{path}/DIT000123.xml \N{WARNING SIGN}\N{VARIATION SELECTOR-16}  is empty !"
        == output
    )


@patch("common.serializers.validate_envelope")
def test_dump_transactions_invalid(
    validate_envelope,
    tmp_path,
    capsys,
    approved_transaction,
):
    validate_envelope.side_effect = etree.DocumentInvalid("invalid")
    assert 0
    factories.GoodsNomenclatureFactory.create(transaction=approved_transaction)
    transactions = approved_transaction.workbasket.transactions.all()
    envelope_id = 123
    directory = tmp_path / "test_directory"
    directory.mkdir()
    util.dump_transactions(transactions, envelope_id, directory, None)
    output = capsys.readouterr().out
    path = directory.__str__()

    assert (
        f"{path}/DIT000123.xml \N{WARNING SIGN}\N{VARIATION SELECTOR-16}  Envelope invalid:"
        == output
    )
