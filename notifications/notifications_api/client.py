from django.conf import settings
from notifications_python_client import prepare_upload
from notifications_python_client.notifications import NotificationsAPIClient
from requests import Response


class NotificationAPIClient:
    def __init__(self) -> None:
        self.client = NotificationsAPIClient(settings.NOTIFICATIONS_API_KEY)

    def send_email(
        self, email_address, template_id, personalisation, **kwargs
    ) -> Response:
        """Send email via the notifications api."""
        return self.client.send_email_notification(
            email_address=email_address,
            template_id=template_id,
            personalisation=personalisation,
            **kwargs,
        )

    def prepare_upload(
        self,
        file,
        is_csv=False,
        confirm_email_before_download=None,
        retention_period=None,
    ) -> object:
        """Prepare a file to be uploaded via the notificaitons client."""
        return prepare_upload(
            file,
            is_csv,
            confirm_email_before_download,
            retention_period,
        )
