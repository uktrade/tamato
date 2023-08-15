from unittest.mock import patch
from uuid import uuid4

import pytest

from common.tests import factories
from notifications import models
from notifications import tasks

pytestmark = pytest.mark.django_db

import pytest

from common.tests import factories
from importer.models import ImportBatchStatus

pytestmark = pytest.mark.django_db


def goods_report_notification():
    factories.NotifiedUserFactory(
        email="goods_report@email.co.uk",  # PS-IGNORE
        enrol_packaging=False,
        enrol_goods_report=True,
    )
    factories.NotifiedUserFactory(
        email="no_goods_report@email.co.uk",  # PS-IGNORE
    )
    import_batch = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        goods_import=True,
        taric_file="goods.xml",
    )

    return factories.GoodsReportNotificationFactory(attachment_id=import_batch.id)


def packaging_notification():
    factories.NotifiedUserFactory(
        email="packaging@email.co.uk",  # PS-IGNORE
    )
    factories.NotifiedUserFactory(
        email="no_packaging@email.co.uk",  # PS-IGNORE
        enrol_packaging=False,
    )
    return factories.PackagingNotificationFactory()


def publishing_notification():
    factories.NotifiedUserFactory(
        email="publishing@email.co.uk",  # PS-IGNORE
        enrol_packaging=False,
        enrol_api_publishing=True,
    )
    factories.NotifiedUserFactory(
        email="no_publishing@email.co.uk",  # PS-IGNORE
    )
    return factories.PublishingNotificationFactory()


@pytest.mark.parametrize(
    "notification_and_user_factory,user_type",
    [
        (
            goods_report_notification,
            "goods_report",
        ),
        (
            packaging_notification,
            "packaging",
        ),
        (
            publishing_notification,
            "publishing",
        ),
    ],
    ids=(
        "goods_report",
        "cds",
        "api",
    ),
)
def test_send_emails(notification_and_user_factory, user_type):
    """Tests that email notifications are only sent to users subscribed to
    email type and that a log is created with this user's email. """

    expected_present_email = f"{user_type}@email.co.uk"  # PS-IGNORE
    expected_unenrolled_email = f"no_{user_type}@email.co.uk"  # PS-IGNORE
    notification = notification_and_user_factory()

    tasks.send_emails.apply(
        kwargs={
            "notification_id": notification.id
        },
    )

    recipients = f"{expected_present_email} \n"
    log = models.NotificationLog.objects.get(
        notification=notification,
        recipients=recipients,
        success=True,
    )

    assert expected_unenrolled_email not in log.recipients

