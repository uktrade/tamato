from importer.models import ImportBatch
from notifications.models import Notification
from notifications.notification_type import GOODS_REPORT
from notifications.notification_type import NotificationType
from notifications.tasks import send_emails


def create_and_send_notificaiton(
    template_id: str,
    email_type: NotificationType,
    attachment_id: int = None,
    personalisation: dict = {},
    **kwargs,
):
    """
    Creates a Notification object then triggers the email task.

    :param template_id: notification tempalte to use
    :param email_type: which type of email is being sent
    :param attachment_id: optional attachment id for the object to send as an attachment
    :param personalisation: personalised data to display in the email
    """
    attachment_object = None
    if email_type == GOODS_REPORT:
        import_batch = ImportBatch.objects.get(id=attachment_id)
        attachment_object = import_batch
    notification = Notification.objects.create(
        template_id, email_type, attachment_object, personalisation, **kwargs
    )
    send_emails.delay(
        notification_id=notification.id,
    )
