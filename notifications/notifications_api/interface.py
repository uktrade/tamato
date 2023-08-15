import base64
import json
import uuid
from abc import ABC
from abc import abstractmethod

from requests import Response

from notifications.notifications_api.client import NotificationAPIClient

DOCUMENT_UPLOAD_SIZE_LIMIT = 2 * 1024 * 1024


class NotificationAPIBase(ABC):
    @abstractmethod
    def send_email(
        self, email_address, template_id, personalisation, **kwargs
    ) -> Response:
        raise NotImplementedError

    @abstractmethod
    def prepare_upload(
        self,
        file,
        is_csv=False,
        confirm_email_before_download=None,
        retention_period=None,
    ) -> object:
        raise NotImplementedError


class NotificationAPIStubbed(NotificationAPIBase):
    """
    Notification API stubbed interface.

    Provides notification api behaviour without calling the external serivce.
    """

    def stubbed_send_email(
        self, email_address, template_id, personalisation, **kwargs
    ) -> Response:
        response = Response()

        if not email_address:
            response._content = bytes(json.dumps(
                "[{'error': 'ValidationError', 'message': 'email_address Not a valid email address'}]" 
            ), "utf-8")
            response.headers["Content-Type"] = "application/json"
            response.status_code = 400
        elif not template_id:
            response._content = bytes(json.dumps(
                "[{'error': 'ValidationError', 'message': 'template_id is not a valid UUID'}]"
            ), "utf-8")
            response.headers["Content-Type"] = "application/json"
            response.status_code = 400
        elif not personalisation:
            response._content = bytes(json.dumps(
                "[{'error': 'BadRequestError', 'message': 'Missing personalisation: stub'}]" 
            ), "utf-8")
            response.headers["Content-Type"] = "application/json"
            response.status_code = 400
        else:
            response.status_code = 200
            response_id = uuid.uuid4()
            response_data = {
                "id": response_id,
                "reference": None,
                "content": {
                    "subject": "Stub notify Email",
                    "body": str(personalisation),
                    "from_email": "tamato@stub_email.co.uk",
                },
                "uri": f"https://api.notifications.stub/v2/notifications/{response_id}",
                "template": {
                    "id": template_id,
                    "version": 1,
                    "uri": f"https://api.notifications.stub/v2/template/{template_id}",
                },
            }
            response._content = bytes(str(response_data))

        return response

    def stubbed_prepare_upload(
        self,
        file,
        is_csv=False,
        confirm_email_before_download=None,
        retention_period=None,
    ) -> object:
        contents = file.read()

        if len(contents) > DOCUMENT_UPLOAD_SIZE_LIMIT:
            raise ValueError("File is larger than 2MB")

        file_data = {
            "file": base64.b64encode(contents).decode("ascii"),  # PS-IGNORE
            "is_csv": is_csv,
            "confirm_email_before_download": confirm_email_before_download,
            "retention_period": retention_period,
        }

        return file_data

    def send_email(
        self, email_address, template_id, personalisation, **kwargs
    ) -> Response:
        """Send email via Notification API."""
        return self.stubbed_send_email(
            email_address, template_id, personalisation, **kwargs
        )

    def prepare_upload(
        self,
        file,
        is_csv=False,
        confirm_email_before_download=None,
        retention_period=None,
    ) -> Response:
        """Prepare a file to be uploaded via Notification API."""
        return self.stubbed_prepare_upload(
            file,
            is_csv,
            confirm_email_before_download,
            retention_period,
        )


class NotificationAPI(NotificationAPIBase):
    def __init__(self):
        super().__init__()
        self.client = NotificationAPIClient()

    def send_email(
        self, email_address, template_id, personalisation, **kwargs
    ) -> Response:
        """Send email via Notification API."""
        return self.client.send_email(
            email_address, template_id, personalisation, **kwargs
        )

    def prepare_upload(
        self,
        file,
        is_csv=False,
        confirm_email_before_download=None,
        retention_period=None,
    ) -> Response:
        """Prepare a file to be uploaded via Notification API."""
        return self.client.prepare_upload(
            file,
            is_csv=False,
            confirm_email_before_download=None,
            retention_period=None,
        )
