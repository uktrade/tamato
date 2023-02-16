import pytest

from common.tests import factories
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from exporter.util import exceptions_as_messages
from exporter.util import item_timer
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_exceptions_as_messages():
    exception_list = {
        "first_exception": [Exception("test")],
        "second_exception": [Exception("test2")],
    }

    messages = exceptions_as_messages(exception_list)

    assert messages == {
        "first_exception": ["raised an test"],
        "second_exception": ["raised an test2"],
    }


def test_item_timer():
    """Verify that item_timer yields a tuple containing the time to retrieve
    each item and the item itself."""
    items = item_timer([1, 2])

    time_taken, item = next(items)

    assert item == 1
    assert isinstance(time_taken, float)
    assert time_taken >= 0.0

    time_taken, item = next(items)

    assert item == 2
    assert isinstance(time_taken, float)
    assert time_taken >= 0.0


def test_envelope_checker():
    """Test that the checker provides the right error messages for failing
    envelope checks."""
    #  This test is being a right pain at the moment. As it's mega hard to make the dump command fail.. I was thinking the best way to test it to some extent
    #  Is to pass the envelope checker function a miss matching envelope and workbasket and check that the right stuff is returned.

    #  The current ballache i'm having is that the transactions I am passing into the serializer don't seem to be getting copied into the envelope?
    #  The actual code works, but It may be something to do with the way I get the transactions.. although when running the test and the real command side by side,
    #  It seems that the formats of transactions that go into the split_render_transactions function match.. so idk whats going wrong there. That's where I'm at.

    # Make a workbasket, add transactions to it
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.QUEUED,
    )
    with factories.TransactionFactory.create(workbasket=workbasket):
        factories.FootnoteTypeFactory()
        factories.AdditionalCodeFactory()
    # import pdb
    # pdb.set_trace()

    # Make a envelope from the files
    output_file_constructor = dit_file_generator("/tmp", 230000)
    serializer = MultiFileEnvelopeTransactionSerializer(
        output_file_constructor,
        envelope_id=230001,
        max_envelope_size=4096,
        # This max envelope size is the minimum, won't let you have less.
    )
    transactions = workbasket.transactions.all()
    envelope = (list(serializer.split_render_transactions(transactions))[0],)

    assert len(envelope.transactions) > 0
    # Then take out a transaction from the workbasket or the envelope..
    # Run the envelope checker
    # Assert that the right checks_pass is false and the transaction count error is returned.
    # Repeat the process but change one of the partitions from 2 to something else..
    # Repeat the process but change one of the id's, maybe by adding a transaction and taking an origial away? ..
