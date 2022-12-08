from unittest.mock import MagicMock
from unittest.mock import patch

import factory
import pytest
from django.conf import settings
from notifications_python_client import prepare_upload

from common.tests import factories
from publishing import models
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_create():
    """Test multiple PackagedWorkBasket instances creation is managed
    correctly."""

    first_packaged_work_basket = factories.PackagedWorkBasketFactory()
    second_packaged_work_basket = factories.PackagedWorkBasketFactory()
    assert first_packaged_work_basket.position > 0
    assert second_packaged_work_basket.position > 0
    assert first_packaged_work_basket.position < second_packaged_work_basket.position


def test_create_duplicate_awaiting_instances():
    """Test that a WorkBasket cannot enter the packaging queue more than
    once."""

    packaged_work_basket = factories.PackagedWorkBasketFactory()
    with pytest.raises(models.PackagedWorkBasketDuplication):
        factories.PackagedWorkBasketFactory(workbasket=packaged_work_basket.workbasket)


def test_create_from_invalid_status():
    """Test that a WorkBasket can only enter the packaging queue when it has a
    valid status."""

    editing_workbasket = factories.WorkBasketFactory(
        status=WorkflowStatus.EDITING,
    )
    with pytest.raises(models.PackagedWorkBasketInvalidCheckStatus):
        factories.PackagedWorkBasketFactory(workbasket=editing_workbasket)


@patch("notifications.tasks.send_emails.delay")
def test_notify_ready_for_processing(send_emails, loading_report_storage):
    with patch(
        "exporter.storages.HMRCStorage.save",
        wraps=MagicMock(side_effect=loading_report_storage.save),
    ):
        packaged_wb = factories.PackagedWorkBasketFactory.create(
            envelope=factories.EnvelopeFactory.create(),
            loading_report__file=factory.django.FileField(filename="the_file.dat"),
        )
    packaged_wb.notify_ready_for_processing()
    personalisation = {
        "envelope_id": packaged_wb.envelope.envelope_id,
        "theme": packaged_wb.theme,
        "eif": "Immediately",
        "jira_url": packaged_wb.jira_url,
    }

    send_emails.assert_called_once_with(
        template_id=settings.READY_FOR_CDS_TEMPLATE_ID,
        personalisation=personalisation,
    )


@patch("notifications.tasks.send_emails.delay")
def test_notify_processing_succeeded(send_emails, loading_report_storage):
    with patch(
        "exporter.storages.HMRCStorage.save",
        wraps=MagicMock(side_effect=loading_report_storage.save),
    ):
        packaged_wb = factories.PackagedWorkBasketFactory.create(
            envelope=factories.EnvelopeFactory.create(),
            loading_report__file=factory.django.FileField(filename="the_file.html"),
        )

    packaged_wb.notify_processing_succeeded()
    f = packaged_wb.loading_report.file.open("rb")
    personalisation = {
        "envelope_id": packaged_wb.envelope.envelope_id,
        "transaction_count": packaged_wb.workbasket.transactions.count(),
        "link_to_file": prepare_upload(f),
    }

    send_emails.assert_called_once_with(
        template_id=settings.CDS_ACCEPTED_TEMPLATE_ID,
        personalisation=personalisation,
    )


@patch("notifications.tasks.send_emails.delay")
def test_notify_processing_failed(send_emails, loading_report_storage):
    with patch(
        "exporter.storages.HMRCStorage.save",
        wraps=MagicMock(side_effect=loading_report_storage.save),
    ):
        packaged_wb = factories.PackagedWorkBasketFactory.create(
            envelope=factories.EnvelopeFactory.create(),
            loading_report__file=factory.django.FileField(filename="the_file.html"),
        )

    packaged_wb.notify_processing_failed()
    f = packaged_wb.loading_report.file.open("rb")
    personalisation = {
        "envelope_id": packaged_wb.envelope.envelope_id,
        "link_to_file": prepare_upload(f),
    }

    send_emails.assert_called_once_with(
        template_id=settings.CDS_REJECTED_TEMPLATE_ID,
        personalisation=personalisation,
    )
