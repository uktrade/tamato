import datetime
import io
import os
import random

import pytest
from bs4 import BeautifulSoup
from lxml import etree
from pytest_django.asserts import assertQuerysetEqual  # noqa

from common.models import Transaction
from common.serializers import EnvelopeSerializer
from common.serializers import deserialize_date
from common.serializers import serialize_date
from common.tests import factories
from common.tests.factories import ApprovedTransactionFactory
from common.tests.factories import QueuedWorkBasketFactory
from common.tests.util import taric_xml_record_codes
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.serializers import RenderedTransactions
from exporter.util import dit_file_generator
from taric.models import Envelope
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_serializer_throws_error_if_max_size_is_too_small():
    """If EnvelopeSerializer gets an max_envelope_size_in_mb is an int < 4k it
    will raise a ValueError otherwise it does not raises no exception."""
    EnvelopeSerializer(io.StringIO(), envelope_id=1, max_envelope_size=4096)

    with pytest.raises(ValueError) as e:
        EnvelopeSerializer(io.StringIO(), envelope_id=1, max_envelope_size=4095)
    assert e.value.args == (
        "Max envelope size 4095 is too small, it should be at least 4096.",
    )


def test_serializer_min_envelope_size_is_large_enough():
    """MIN_ENVELOPE_SIZE needs to be large enough to hold the templates the
    templates for the envelope and some content."""
    serializer = EnvelopeSerializer(io.StringIO(), 1)

    min_content_size = 1024  # minimum size for content.
    templates_size = len(
        (
            serializer.render_file_header()
            + serializer.render_envelope_start()
            + serializer.render_envelope_end()
        ).encode(),
    )

    assert EnvelopeSerializer.MIN_ENVELOPE_SIZE > templates_size + min_content_size


def test_envelope_serializer_outputs_expected_items(queued_workbasket):
    """EnvelopeSerializer should output all the models passed to it and
    generated records for descriptions."""
    # Transaction context manager is not used to create transactions,
    # as it creates phantom workbaskets and transactions which cause XSD failures later.
    tx = ApprovedTransactionFactory.create(workbasket=queued_workbasket)
    regulation = factories.RegulationFactory.create(
        transaction=tx,
        regulation_group=None,
    )
    footnote = factories.FootnoteFactory.create(
        transaction=tx,
    )  # FootnoteFactory also creates a FootnoteType and FootnoteDescription

    expected_items = [
        regulation,
        footnote.footnote_type,
        footnote,
        *footnote.descriptions.all(),
    ]  # < Note: These are sorted by record_code, subrecord_code
    expected_item_record_codes = {
        (o.record_code, o.subrecord_code) for o in expected_items
    }

    assertQuerysetEqual(
        expected_items,
        queued_workbasket.tracked_models.all(),
        transform=lambda o: o,
        ordered=False,
    )  # Some of the factories create other data so sanity check expected items.

    output = io.BytesIO()
    with EnvelopeSerializer(output, random.randint(2, 9999)) as env:
        env.render_transaction(
            models=queued_workbasket.tracked_models.all(),
            transaction_id=tx.order,
        )

    output_xml = etree.XML(output.getvalue())
    output_record_codes = {*taric_xml_record_codes(output_xml)}

    # More items than models are output, as models for descriptions aren't kept.
    assert (
        output_record_codes >= expected_item_record_codes
    ), f"Output ({output_record_codes}) missing some expected record codes"


def test_transaction_envelope_serializer_splits_output():
    """
    Verify MultiFileEnvelopeTransactionSerializer outputs the tracked_models
    passed to it and generates records for descriptions.

    This test is a bit artificial: testing 40mb splitting would be inefficient,
    max_envelope_size is set to 7k, small enough to trigger envelope splitting
    after just one transaction.
    """
    # Add transactions with different kinds of data to the workbasket.
    queued_workbasket = QueuedWorkBasketFactory.create()
    with ApprovedTransactionFactory.create(workbasket=queued_workbasket) as tx1:
        factories.RegulationFactory.create()

    with ApprovedTransactionFactory.create(workbasket=queued_workbasket) as tx2:
        factories.RegulationFactory.create(regulation_group=None),
        factories.FootnoteTypeFactory.create()

    with ApprovedTransactionFactory.create(workbasket=queued_workbasket) as tx3:
        factories.FootnoteTypeFactory.create()

    transactions = Transaction.objects.filter(pk__in=[tx1.pk, tx2.pk, tx3.pk])
    expected_transactions = [
        Transaction.objects.filter(pk=tx.pk) for tx in [tx1, tx2, tx3]
    ]
    expected_record_codes = [
        [
            (tracked_model.record_code, tracked_model.subrecord_code)
            for tracked_model in tx.tracked_models.all()
        ]
        for tx in [tx1, tx2, tx3]
    ]

    # Create a static buffers to output to + a function to grab each one in turn to use as the constructor.
    expected_outputs = [io.BytesIO(), io.BytesIO(), io.BytesIO()]

    def create_output_constructor():
        output_iter = iter(expected_outputs)
        return lambda: next(output_iter)

    serializer = MultiFileEnvelopeTransactionSerializer(
        create_output_constructor(),
        envelope_id=int(Envelope.next_envelope_id()),
        max_envelope_size=7000,
    )

    for i, rendered_envelope in enumerate(
        serializer.split_render_transactions(transactions),
    ):
        # Base assumption is that this yields RenderedTransactions
        assert isinstance(rendered_envelope, RenderedTransactions)

        assert rendered_envelope.output == expected_outputs[i]
        assert rendered_envelope.is_oversize is False
        assert 0 < rendered_envelope.output.tell() < 7000

        assert len(
            rendered_envelope.transactions,
        ), "Serializer should skip empty transactions, they cause XSD validation to fail."

        assert sorted(rendered_envelope.transactions) == sorted(
            expected_transactions[i],
        )

        # Verify the XML output
        output_xml = etree.XML(rendered_envelope.output.getvalue())
        output_record_codes = {*taric_xml_record_codes(output_xml)}

        # TODO - it would be good to check the output more thoroughly than just the record code.
        # Some record codes are generated in the template, making issuperset required in this assertion.
        assert output_record_codes.issuperset(expected_record_codes[i])


def test_transaction_envelope_serializer_counters(queued_workbasket):
    """Test that the envelope serializer sets the counters in an envelope
    correctly that the message id always starts from one in each envelope and
    that the record sequence number increments."""
    approved_transaction = queued_workbasket.transactions.approved().last()
    # add a tracked_models to the workbasket

    factories.AdditionalCodeTypeFactory(transaction=approved_transaction)
    factories.AdditionalCodeDescriptionFactory(transaction=approved_transaction)
    factories.RegulationFactory(
        transaction=approved_transaction,
        regulation_group=factories.RegulationGroupFactory(
            transaction=approved_transaction,
        ),
    )
    factories.CertificateFactory(
        transaction=approved_transaction,
        certificate_type=factories.CertificateTypeFactory(
            transaction=approved_transaction,
        ),
        description=factories.CertificateDescriptionFactory(
            transaction=approved_transaction,
        ),
    )
    factories.FootnoteFactory(
        transaction=approved_transaction,
        description=factories.FootnoteDescriptionFactory(
            transaction=approved_transaction,
        ),
        footnote_type=factories.FootnoteTypeFactory(transaction=approved_transaction),
    )

    # Make a envelope from the files
    output_file_constructor = dit_file_generator("/tmp", 230001)
    serializer = MultiFileEnvelopeTransactionSerializer(
        output_file_constructor,
        envelope_id=230001,
    )

    workbaskets = WorkBasket.objects.filter(pk=queued_workbasket.pk)
    transactions = workbaskets.ordered_transactions()

    envelope = list(serializer.split_render_transactions(transactions))[0]

    assert len(envelope.transactions) > 0

    envelope_file = envelope.output
    envelope_file.seek(0, os.SEEK_SET)
    soup = BeautifulSoup(envelope_file, "xml")
    record_sequence_numbers = soup.find_all("oub:record.sequence.number")
    message_id_numbers = soup.find_all("env:app.message")

    expected_value = 1
    for element in record_sequence_numbers:
        actual_value = int(element.text)
        assert actual_value == expected_value
        expected_value += 1

    expected_id = 1
    for element in message_id_numbers:
        actual_value = int(element["id"])
        assert actual_value == expected_id
        expected_id += 1

    workbasket = factories.QueuedWorkBasketFactory.create()
    approved_transaction2 = workbasket.transactions.approved().last()
    factories.AdditionalCodeTypeFactory(transaction=approved_transaction2)
    factories.AdditionalCodeDescriptionFactory(transaction=approved_transaction2)
    factories.FootnoteFactory(
        transaction=approved_transaction2,
        description=factories.FootnoteDescriptionFactory(
            transaction=approved_transaction2,
        ),
        footnote_type=factories.FootnoteTypeFactory(transaction=approved_transaction2),
    )

    # Make a envelope from the files
    output_file_constructor = dit_file_generator("/tmp", 230002)
    serializer = MultiFileEnvelopeTransactionSerializer(
        output_file_constructor,
        envelope_id=230002,
    )

    workbaskets = WorkBasket.objects.filter(pk=workbasket.pk)
    transactions = workbaskets.ordered_transactions()

    envelope_2 = list(serializer.split_render_transactions(transactions))[0]

    assert len(envelope.transactions) > 0

    envelope_file_2 = envelope_2.output
    envelope_file_2.seek(0, os.SEEK_SET)
    soup_2 = BeautifulSoup(envelope_file_2, "xml")
    message_id_numbers_2 = soup_2.find_all("env:app.message")

    expected_id_2 = 1
    for element in message_id_numbers_2:
        actual_value = int(element.get("id"))
        assert actual_value == expected_id_2
        expected_id_2 += 1


@pytest.mark.parametrize(
    "test_date, serialized_truthiness",
    [
        (datetime.date.today(), True),
        (datetime.date(1900, 1, 1), True),
        (datetime.date(1970, 1, 1), True),
        (datetime.date(3000, 1, 1), True),
        (None, False),
    ],
)
def test_date_serialization(
    test_date: datetime.date,
    serialized_truthiness: bool,
):
    serialized_date = serialize_date(test_date)
    assert bool(serialized_date) == serialized_truthiness

    deserialized_date = deserialize_date(serialized_date)
    assert deserialized_date == test_date
