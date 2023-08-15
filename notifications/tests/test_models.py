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
        "goods_report_notification",
        "packaging_notification",
        "publishing_notification",
    ),
)
def test_create_notification(notification_and_user_factory, user_type):
    """Test that the submit-for-packaging button is disabled when a notification
    has not been sent for a commodity code import (goods)"""

    expected_present_email = f"{user_type}@email.co.uk"  # PS-IGNORE
    expected_not_present_email = f"no_{user_type}@email.co.uk"  # PS-IGNORE
    notification = notification_and_user_factory()

    users = notification.notified_users.all()

    for user in users:
        assert user.email == expected_present_email
        assert user.email != expected_not_present_email
