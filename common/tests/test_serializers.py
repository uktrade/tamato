import io
import random

import pytest
from lxml import etree
from pytest_django.asserts import assertQuerysetEqual  # noqa

from common.models import Transaction
from common.serializers import EnvelopeSerializer
from common.tests import factories
from common.tests.factories import ApprovedTransactionFactory
from common.tests.factories import ApprovedWorkBasketFactory
from common.tests.util import taric_xml_record_codes
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.serializers import RenderedTransactions
from taric.models import Envelope

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


def test_envelope_serializer_outputs_expected_items(approved_workbasket):
    """EnvelopeSerializer should output all the models passed to it and
    generated records for descriptions."""
    # Transaction context manager is not used to create transactions,
    # as it creates phantom workbaskets and transactions which cause XSD failures later.
    tx = ApprovedTransactionFactory.create(workbasket=approved_workbasket)
    regulation = factories.RegulationFactory.create(
        transaction=tx,
        regulation_group=None,
    )
    footnote = factories.FootnoteFactory.create(
        transaction=tx,
    )  # FootnoteFactory also creates a FootnoteDescription

    expected_items = [
        regulation,
        footnote,
        *footnote.descriptions.all(),
    ]  # < Note: These are sorted by record_code, subrecord_code
    expected_item_record_codes = {
        (o.record_code, o.subrecord_code) for o in expected_items
    }

    assertQuerysetEqual(
        expected_items,
        approved_workbasket.tracked_models.all(),
        transform=lambda o: o,
        ordered=False,
    )  # Some of the factories create other data so sanity check expected items.

    output = io.BytesIO()
    with EnvelopeSerializer(output, random.randint(2, 9999)) as env:
        env.render_transaction(
            transactions=approved_workbasket.transactions,
        )

    output_xml = etree.XML(output.getvalue())
    output_record_codes = {*taric_xml_record_codes(output_xml)}

    # More items than models are output, as models for descriptions aren't kept.
    assert output_record_codes.issuperset(expected_item_record_codes)


def test_transaction_envelope_serializer_splits_output():
    """
    Verify MultiFileEnvelopeTransactionSerializer outputs the tracked_models
    passed to it and generates records for descriptions.

    This test is a bit artificial: testing 40mb splitting would be inefficient,
    max_envelope_size is set to 7k, small enough to trigger envelope splitting
    after just one transaction.
    """
    # Add transactions with different kinds of data to the workbasket.
    approved_workbasket = ApprovedWorkBasketFactory.create()
    with ApprovedTransactionFactory.create(workbasket=approved_workbasket) as tx1:
        factories.RegulationFactory.create()

    with ApprovedTransactionFactory.create(workbasket=approved_workbasket) as tx2:
        factories.RegulationFactory.create(regulation_group=None),
        factories.FootnoteTypeFactory.create()

    with ApprovedTransactionFactory.create(workbasket=approved_workbasket) as tx3:
        factories.FootnoteTypeFactory.create()

    transactions = Transaction.objects.filter(pk__in=[tx1.pk, tx2.pk, tx3.pk])
    expected_transactions = [
        Transaction.objects.filter(pk=tx.pk).values_list("pk", flat=True)
        for tx in [tx1, tx2, tx3]
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
