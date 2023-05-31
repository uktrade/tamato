import requests
from django.conf import settings
from requests import Response

from publishing.models.envelope import Envelope
from publishing.models.envelope import EnvelopeId


class TariffAPIClient:
    def __init__(self) -> None:
        self.api_host = settings.API_HOST
        self.api_url_path = settings.API_URL_PATH

        self.api_key = settings.API_KEY

    def get_envelope(self, envelope_id: EnvelopeId) -> Response:
        """Get envelope from Tariff API production environment."""
        full_api_url = self.api_host + self.api_url_path + envelope_id

        headers = {
            "X-API-KEY": self.api_key,
        }

        response = requests.get(full_api_url, headers=headers, timeout=60)
        return response

    def post_envelope(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API."""
        full_api_url = self.api_host + self.api_url_path + envelope.envelope_id

        headers = {
            "X-API-KEY": self.api_key,
        }
        files = {
            "file": envelope.xml_file.open(mode="rb"),
        }

        response = requests.post(full_api_url, headers=headers, files=files, timeout=60)
        return response
