import pytest

from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from publishing.util import envelope_checker
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_envelope_checker(queued_workbasket_factory):
    """Test that the checker passes on valid workbasket."""

    # queued workbasket built with approved transaction and tracked models
    workbasket = queued_workbasket_factory()

    # Make a envelope from the files
    output_file_constructor = dit_file_generator("/tmp", 230001)
    serializer = MultiFileEnvelopeTransactionSerializer(
        output_file_constructor,
        envelope_id=230001,
    )

    workbaskets = WorkBasket.objects.filter(pk=workbasket.pk)
    transactions = workbaskets.ordered_transactions()

    envelope = list(serializer.split_render_transactions(transactions))[0]

    assert len(envelope.transactions) > 0
    assert envelope.transactions[0].tracked_models.count() == 3

    results = envelope_checker(workbaskets, envelope)

    assert results["checks_pass"] is True


def test_envelope_checker_transaction_mismatch(queued_workbasket):
    """Test that the checker provides the right error messages for failing
    envelope checks."""

    # empty workbasket but has an approved transaction
    workbasket = queued_workbasket

    # Make a envelope from the files
    output_file_constructor = dit_file_generator("/tmp", 230001)
    serializer = MultiFileEnvelopeTransactionSerializer(
        output_file_constructor,
        envelope_id=230001,
    )

    workbaskets = WorkBasket.objects.filter(pk=workbasket.pk)
    transactions = workbaskets.ordered_transactions()

    envelope = list(serializer.split_render_transactions(transactions))[0]

    results = envelope_checker(workbaskets, envelope)

    assert results["checks_pass"] is False
    assert (
        "Envelope does not contain all transactions!" in results["error_message_list"]
    )
