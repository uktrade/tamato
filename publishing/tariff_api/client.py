import requests
from django.conf import settings
from requests import Response

from publishing.models.envelope import Envelope
from publishing.models.envelope import EnvelopeId


class TariffAPIClient:
    def __init__(self) -> None:
        self.api_host_staging = settings.API_HOST_STAGING
        self.api_host_prod = settings.API_HOST_PROD
        self.api_url_path = settings.API_URL_PATH

        self.api_key_staging_get = settings.API_KEY_STAGING_GET
        self.api_key_prod_get = settings.API_KEY_PROD_GET

        self.api_key_staging_post = settings.API_KEY_STAGING_POST
        self.api_key_prod_post = settings.API_KEY_PROD_POST

    def get_envelope_staging(self, envelope_id: EnvelopeId) -> Response:
        """Get envelope from Tariff API staging environment."""
        full_api_url = self.api_host_staging + self.api_url_path + envelope_id

        headers = {
            "X-API-KEY": self.api_key_staging_get,
        }

        response = requests.get(full_api_url, headers=headers, timeout=60)
        return response

    def get_envelope_production(self, envelope_id: EnvelopeId) -> Response:
        """Get envelope from Tariff API production environment."""
        full_api_url = self.api_host_prod + self.api_url_path + envelope_id

        headers = {
            "X-API-KEY": self.api_key_staging_get,
        }

        response = requests.get(full_api_url, headers=headers, timeout=60)
        return response

    def post_envelope_staging(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API staging environment."""
        full_api_url = self.api_host_staging + self.api_url_path + envelope.envelope_id

        headers = {
            "X-API-KEY": self.api_key_staging_post,
        }
        files = {
            "file": envelope.xml_file.open(mode="rb"),
        }

        response = requests.post(full_api_url, headers=headers, files=files, timeout=60)
        return response

    def post_envelope_production(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API production environment."""
        full_api_url = self.api_host_prod + self.api_url_path + envelope.envelope_id

        headers = {
            "X-API-KEY": self.api_key_prod_post,
        }
        files = {
            "file": envelope.xml_file.open(mode="rb"),
        }

        response = requests.post(full_api_url, headers=headers, files=files, timeout=60)
        return response
