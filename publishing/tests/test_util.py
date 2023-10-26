import os

import pytest
from lxml.etree import DocumentInvalid

from common.tests import factories
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from publishing.util import TaricDataAssertionError
from publishing.util import validate_envelope
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db

TEST_FILES_PATH = os.path.join(os.path.dirname(__file__), "test_files")


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


def test_all_tracked_models_validate_envelope(queued_workbasket):
    """Test that the checker passes on valid workbasket with all tracked
    models."""

    approved_transaction = queued_workbasket.transactions.approved().last()
    # add a tracked_models to the workbasket

    factories.GeographicalMembershipFactory(
        transaction=approved_transaction,
        member=factories.GeographicalAreaFactory(
            transaction=approved_transaction,
            description=factories.GeographicalAreaDescriptionFactory(
                transaction=approved_transaction,
            ),
        ),
    )
    factories.AdditionalCodeTypeFactory(transaction=approved_transaction)
    factories.AdditionalCodeDescriptionFactory(transaction=approved_transaction)

    reg1 = factories.RegulationFactory(
        transaction=approved_transaction,
        regulation_group=factories.RegulationGroupFactory(
            transaction=approved_transaction,
        ),
    )
    reg2 = factories.RegulationFactory(
        transaction=approved_transaction,
    )
    factories.AmendmentFactory(
        transaction=approved_transaction,
        target_regulation=reg2,
        enacting_regulation=reg1,
    )
    factories.SuspensionFactory(
        transaction=approved_transaction,
        target_regulation=reg2,
        enacting_regulation=reg1,
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

    coms = factories.GoodsNomenclatureFactory(
        transaction=approved_transaction,
        indent=factories.GoodsNomenclatureIndentFactory(
            transaction=approved_transaction,
        ),
        description=factories.GoodsNomenclatureDescriptionFactory(
            transaction=approved_transaction,
        ),
        origin=factories.GoodsNomenclatureOriginFactory(
            transaction=approved_transaction,
        ),
    )
    factories.GoodsNomenclatureSuccessorFactory(transaction=approved_transaction)

    foot = factories.FootnoteFactory(
        transaction=approved_transaction,
        description=factories.FootnoteDescriptionFactory(
            transaction=approved_transaction,
        ),
        footnote_type=factories.FootnoteTypeFactory(transaction=approved_transaction),
    )

    factories.FootnoteAssociationGoodsNomenclatureFactory(
        transaction=approved_transaction,
        goods_nomenclature=coms,
        associated_footnote=foot,
    )

    duty = factories.DutyExpressionFactory(transaction=approved_transaction)
    measure = factories.MeasureFactory(transaction=approved_transaction)
    money_unit = factories.MonetaryUnitFactory(transaction=approved_transaction)
    measure_condition = factories.MeasureConditionFactory(
        transaction=approved_transaction,
        dependent_measure=measure,
        condition_code=factories.MeasureConditionCodeFactory(
            transaction=approved_transaction,
        ),
        monetary_unit=money_unit,
        action=factories.MeasureActionFactory(transaction=approved_transaction),
    )

    factories.MeasureConditionComponentFactory(
        transaction=approved_transaction,
        condition=measure_condition,
        duty_expression=duty,
        monetary_unit=money_unit,
    )
    factories.MeasureComponentFactory(
        transaction=approved_transaction,
        component_measure=measure,
        duty_expression=duty,
    )
    factories.AdditionalCodeTypeMeasureTypeFactory(transaction=approved_transaction)
    factories.FootnoteAssociationMeasureFactory(transaction=approved_transaction)
    factories.MeasureExcludedGeographicalAreaFactory(transaction=approved_transaction)
    factories.MeasureTypeSeriesFactory(transaction=approved_transaction)
    factories.MeasureTypeFactory(transaction=approved_transaction)

    factories.MeasurementUnitQualifierFactory(transaction=approved_transaction)
    factories.MeasurementUnitFactory(transaction=approved_transaction)
    factories.MeasurementFactory(transaction=approved_transaction)
    factories.MeasurementFactory(
        transaction=approved_transaction,
        measurement_unit_qualifier=None,
    )

    factories.QuotaAssociationFactory(transaction=approved_transaction)
    factories.QuotaBlockingFactory(transaction=approved_transaction)
    factories.QuotaDefinitionFactory(transaction=approved_transaction)
    factories.QuotaEventFactory(transaction=approved_transaction)
    factories.QuotaOrderNumberOriginExclusionFactory(transaction=approved_transaction)
    factories.QuotaOrderNumberOriginFactory(transaction=approved_transaction)
    factories.QuotaOrderNumberFactory(transaction=approved_transaction)
    factories.QuotaSuspensionFactory(transaction=approved_transaction)

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


def test_validate_envelope_records_out_of_order(queued_workbasket):
    """Test that the checker provides the right error messages for failing
    envelope checks."""

    approved_transaction = queued_workbasket.transactions.approved().last()

    factories.FootnoteTypeFactory(transaction=approved_transaction)
    factories.FootnoteDescriptionFactory(transaction=approved_transaction)
    factories.FootnoteFactory(transaction=approved_transaction)

    # Make a envelope from the files
    output_file_constructor = dit_file_generator("/tmp", 230001)
    serializer = MultiFileEnvelopeTransactionSerializer(
        output_file_constructor,
        envelope_id=230001,
    )

    workbaskets = WorkBasket.objects.filter(pk=queued_workbasket.pk)
    transactions = workbaskets.ordered_transactions()

    envelope = list(serializer.split_render_transactions(transactions))[0]
    envelope_file = envelope.output
    with pytest.raises(TaricDataAssertionError) as e:
        envelope_file.seek(0, os.SEEK_SET)
        validate_envelope(envelope_file, workbaskets=workbaskets)
        assert "Elements out of order in XML:" in e


def test_validate_envelope_no_declaration(caplog):
    """Test that validated envelopes containing no XML declaration element
    correctly log a warning message."""

    with open(f"{TEST_FILES_PATH}/envelope_no_declaration.xml", "rb") as envelope_file:
        workbaskets = WorkBasket.objects.none()

        try:
            import logging

            # Ensure logging propagation is enabled else log messages won't
            # reach this module.
            logger = logging.getLogger("publishing")
            logger.propagate = True

            with caplog.at_level(logging.WARNING):
                validate_envelope(
                    envelope_file,
                    workbaskets=workbaskets,
                    skip_declaration=False,
                )
        except (DocumentInvalid, TaricDataAssertionError):
            # Ignore DocumentInvalid and TaricDataAssertionError exceptions as
            # this test is only concerned with checking the XML declaration
            # part of validate_envelope()
            pass

        assert "Expected XML declaration" in caplog.text
