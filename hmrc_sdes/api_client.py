from apiclient import APIClient
from apiclient import JsonRequestFormatter
from django.conf import settings
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session


class HmrcSdesClient(APIClient):
    """Client for HMRC Secure Data Exchange Notifications API.

    See https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/secure-data-exchange-notifications/1.0
    """

    base_url = "https://test-api.service.hmrc.gov.uk"

    def __init__(self):
        super().__init__(
            request_formatter=JsonRequestFormatter,
        )

        oauth = OAuth2Session(
            client=BackendApplicationClient(settings.HMRC["client_id"]),
            scope=[
                "write:transfer-complete",
                "write:transfer-ready",
            ],
        )
        params = dict(
            token_url=settings.HMRC["token_url"],
            client_id=settings.HMRC["client_id"],
            client_secret=settings.HMRC["client_secret"],
            include_client_id=True,
            scope=[
                "write:transfer-complete",
                "write:transfer-ready",
            ],
        )
        oauth.fetch_token(**params)
        self.set_session(oauth)

        self.srn = settings.HMRC["service_reference_number"]

    def get_default_headers(self) -> dict:
        return dict(
            **super().get_default_headers(),
            **{
                "Content-Type": "application/vnd.hmrc.1.0+json; charset=UTF-8",
                "Accept": "application/vnd.hmrc.1.0+json",
            },
        )

    def notify_transfer_complete(self, upload):
        """Notifies that a given bulk file transfer is complete"""

        return self.post(
            f"{self.base_url}/organisations/notification/files/transfer/complete/{self.srn}",
            data=upload.notification_payload,
        )

    def notify_transfer_ready(self, upload):
        """Notifies that a given bulk file transfer is ready for processing"""

        return self.post(
            f"{self.base_url}/organisations/notification/files/transfer/ready/{self.srn}",
            data=upload.notification_payload,
        )
