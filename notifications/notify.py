import logging
from tempfile import NamedTemporaryFile
from typing import List

from django.conf import settings
from notifications_python_client import prepare_upload
from notifications_python_client.notifications import NotificationsAPIClient

from importer.goods_report import GoodsReporter

logger = logging.getLogger(__name__)


def get_notifications_client():
    return NotificationsAPIClient(settings.NOTIFICATIONS_API_KEY)


def prepare_link_to_file(
    file,
    is_csv=False,
    confirm_email_before_download=None,
    retention_period=None,
):
    """
    Prepare importer file to upload. Improvement possibility have file pre
    genreated and in s3 possibly.

    params:
        file: file which to generate report from
        is_csv: if the file being attached is a csv set to True, default False
        confirm_email_before_download: security feature where user opening files must be on Gov Notify email list
        retention_period: how long the file link is valid for, default 6 months
    """

    with NamedTemporaryFile(suffix=".xlsx") as tmp:
        reporter = GoodsReporter(file)
        goods_report = reporter.create_report()
        goods_report.xlsx_file(tmp)
        return prepare_upload(
            tmp,
            is_csv,
            confirm_email_before_download,
            retention_period,
        )


def send_emails(template_id, personalisation: dict, email_addresses: List[str]) -> dict:
    """
    Generic send emails function which triggers a notification to Gov notify.

    params:
        template_id: email template Id
        personalisation: email personalisation
        email_addresses: list of emails to send emails to

    returns:
        dict(
            "response_ids": string of successful email response ids
            "recipients": string of successful emails recipients
            "failed_recipients": string of unsuccessful emails recipients
        )
    """
    notification_client = get_notifications_client()
    recipients = ""
    failed_recipients = ""
    response_ids = ""
    for email in email_addresses:
        try:
            response = notification_client.send_email_notification(
                email_address=email,
                template_id=template_id,
                personalisation=personalisation,
            )
            response_ids += f"{response['id']} \n"
            recipients += f"{email} \n"
        except Exception as e:
            failed_recipients += f"{email} \n"
            logger.error(
                f"Failed to send email notification to {email}, with status code {e.status_code}.",
            )

    return {
        "response_ids": response_ids,
        "recipients": recipients,
        "failed_recipients": failed_recipients,
    }
