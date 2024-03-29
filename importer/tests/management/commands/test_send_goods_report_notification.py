from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "args, exception_type, error_msg",
    [
        (
            [""],
            CommandError,
            "Error: unrecognized arguments:",
        ),
        (
            ["--import-batch-id", "1234"],
            CommandError,
            "No ImportBatch instance found with pk=1234",
        ),
    ],
)
def test_send_goods_report_notification_required_arguments(
    args,
    exception_type,
    error_msg,
):
    """Test that `send_goods_report_notification` command raises errors when
    invalid arguments are provided."""
    with pytest.raises(exception_type, match=error_msg):
        call_command("send_goods_report_notification", *args)


def test_send_goods_report_notification(
    completed_goods_import_batch,
):
    """Test that `send_goods_report_notification` command triggers an email
    notification."""

    with patch(
        "notifications.models.send_emails_task",
        return_value=MagicMock(),
    ) as mocked_email_task:
        call_command(
            "send_goods_report_notification",
            "--import-batch-id",
            str(completed_goods_import_batch.id),
        )
        mocked_email_task.assert_called_once()
