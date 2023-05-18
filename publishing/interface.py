from abc import ABC
from abc import abstractmethod

from django.conf import settings
from django.utils.module_loading import import_string
from requests import Response

from publishing.client import TariffAPIClient
from publishing.models import Envelope


class TariffAPIBase(ABC):
    @abstractmethod
    def post_envelope_staging(self, envelope: Envelope) -> Response:
        raise NotImplementedError

    @abstractmethod
    def post_envelope_production(self, envelope: Envelope) -> Response:
        raise NotImplementedError


class TariffAPIStubbed(TariffAPIBase):
    def stubbed_post_response(self, envelope: Envelope) -> Response:
        response = Response()

        if not envelope:
            response.reason = "400 No file uploaded"
            response.status_code = 400
        else:
            response.status_code = 200
            response.reason = "200 OK File uploaded"
        return response

    def post_envelope_staging(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API staging environment."""
        return self.stubbed_post_response(envelope=envelope)

    def post_envelope_production(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API production environment."""
        return self.stubbed_post_response(envelope=envelope)


class TariffAPI(TariffAPIBase):
    def __init__(self):
        super().__init__()
        self.client = TariffAPIClient()

    def post_envelope_staging(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API staging environment."""
        return self.client.post_envelope_staging(envelope=envelope)

    def post_envelope_production(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API production environment."""
        return self.client.post_envelope_production(envelope=envelope)


def get_tariff_api_interface() -> TariffAPIBase:
    """Get the Tariff API interface from the TARIFF_API_INTERFACE setting."""
    if not settings.TARIFF_API_INTERFACE:
        return TariffAPIStubbed()

    interface_class = import_string(settings.TARIFF_API_INTERFACE)
    if not issubclass(interface_class, TariffAPIBase):
        raise ValueError("TARIFF_API_INTERFACE must inherit from TariffAPIBase")

    return interface_class()
