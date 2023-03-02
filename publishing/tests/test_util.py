import os

import pytest

from common.tests import factories
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from publishing.util import TaricDataAssertionError
from publishing.util import validate_envelope
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_validate_envelope(queued_workbasket_factory):
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

    envelope_file = envelope.output
    envelope_file.seek(0, os.SEEK_SET)
    validate_envelope(envelope_file, workbaskets=workbaskets)


def test_all_tracked_models_validate_envelope(queued_workbasket_factory):
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

    envelope_file = envelope.output
    envelope_file.seek(0, os.SEEK_SET)
    validate_envelope(envelope_file, workbaskets=workbaskets)


def test_validate_envelope_transaction_mismatch(queued_workbasket):
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
    envelope_file = envelope.output
    with pytest.raises(TaricDataAssertionError) as e:
        envelope_file.seek(0, os.SEEK_SET)
        validate_envelope(envelope_file, workbaskets=workbaskets)
        assert "Envelope does not have any transactions!" in e


def test_validate_envelope_passes_with_an_empty_transaction(queued_workbasket_factory):
    """
    Test that the checker provides the right error messages for failing envelope
    checks.

    Test envelope checker passes when there are empty transactions after
    tracked_models deleted. Have one valid tracked model in one transaction in
    the workbasket
    """

    # queued workbasket built with approved transaction and tracked models
    workbasket = queued_workbasket_factory()

    # add an empty transaction
    factories.ApprovedTransactionFactory.create(workbasket=workbasket)

    # Make a envelope from the files
    output_file_constructor = dit_file_generator("/tmp", 230001)
    serializer = MultiFileEnvelopeTransactionSerializer(
        output_file_constructor,
        envelope_id=230001,
    )

    workbaskets = WorkBasket.objects.filter(pk=workbasket.pk)
    transactions = workbaskets.ordered_transactions()

    envelope = list(serializer.split_render_transactions(transactions))[0]

    envelope_file = envelope.output
    # with pytest.raises(TaricDataAssertionError):
    envelope_file.seek(0, os.SEEK_SET)
    validate_envelope(envelope_file, workbaskets=workbaskets)


def test_validate_envelope_fails_for_missing_tracked_model(queued_workbasket_factory):
    """
    Test that the checker provides the right error messages for failing envelope
    checks.

    Test envelope checker fails when there are missing transactions count of
    tracked models in xml != count of tracked models in workbasket
    """

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

    # add a tracked_models to the workbasket
    factories.AdditionalCodeTypeFactory(
        transaction=workbasket.transactions.approved().last(),
    )
    workbaskets = WorkBasket.objects.filter(pk=workbasket.pk)

    envelope_file = envelope.output
    with pytest.raises(TaricDataAssertionError) as e:
        envelope_file.seek(0, os.SEEK_SET)
        validate_envelope(envelope_file, workbaskets=workbaskets)
        assert "Missing records in XML" in e
