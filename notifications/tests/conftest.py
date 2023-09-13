from unittest.mock import patch

import pytest

from common.tests import factories
from importer.models import ImportBatchStatus


@pytest.fixture()
def goods_report_notification():
    factories.NotifiedUserFactory(
        email="goods_report@email.co.uk",  # /PS-IGNORE
        enrol_packaging=False,
        enrol_goods_report=True,
    )
    factories.NotifiedUserFactory(
        email="no_goods_report@email.co.uk",  # /PS-IGNORE
    )
    import_batch = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        goods_import=True,
        taric_file="goods.xml",
    )

    return factories.GoodsSuccessfulImportNotificationFactory(
        notified_object_pk=import_batch.id,
    )


@pytest.fixture()
def ready_for_packaging_notification(published_envelope_factory):
    factories.NotifiedUserFactory(
        email="packaging@email.co.uk",  # /PS-IGNORE
    )
    factories.NotifiedUserFactory(
        email="no_packaging@email.co.uk",  # /PS-IGNORE
        enrol_packaging=False,
    )
    packaged_wb = published_envelope_factory()
    return factories.EnvelopeReadyForProcessingNotificationFactory(
        notified_object_pk=packaged_wb.id,
    )


@pytest.fixture()
def successful_publishing_notification(crown_dependencies_envelope_factory):
    factories.NotifiedUserFactory(
        email="publishing@email.co.uk",  # /PS-IGNORE
        enrol_packaging=False,
        enrol_api_publishing=True,
    )
    factories.NotifiedUserFactory(
        email="no_publishing@email.co.uk",  # /PS-IGNORE
    )
    cde = crown_dependencies_envelope_factory()
    return factories.CrownDependenciesEnvelopeSuccessNotificationFactory(
        notified_object_pk=cde.id,
    )


@pytest.fixture()
def mock_notify_send_emails():
    with patch(
        "notifications.notify.send_emails",
    ) as mocked_send_emails:
        yield mocked_send_emails


@pytest.fixture()
def mock_prepare_link():
    return_value = {
        "file": "VGVzdA==",
        "is_csv": False,
        "confirm_email_before_download": True,
        "retention_period": None,
    }
    with patch(
        "notifications.notify.prepare_link_to_file",
        return_value=return_value,
    ) as mocked_prepare_link_to_file:
        yield mocked_prepare_link_to_file
