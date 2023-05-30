from abc import ABC
from abc import abstractmethod

from requests import Response

from publishing.models.envelope import Envelope
from publishing.models.envelope import EnvelopeId
from publishing.tariff_api.client import TariffAPIClient


class TariffAPIBase(ABC):
    @abstractmethod
    def get_envelope_staging(self, envelope_id: EnvelopeId) -> Response:
        raise NotImplementedError

    @abstractmethod
    def get_envelope_production(self, envelope_id: EnvelopeId) -> Response:
        raise NotImplementedError

    @abstractmethod
    def post_envelope_staging(self, envelope: Envelope) -> Response:
        raise NotImplementedError

    @abstractmethod
    def post_envelope_production(self, envelope: Envelope) -> Response:
        raise NotImplementedError


class TariffAPIStubbed(TariffAPIBase):
    def stubbed_get_response(self, envelope_id: EnvelopeId = None) -> Response:
        response = Response()
        if not envelope_id:
            response.reason = "404 Taric file does not exist"
            response.status_code = 404
        elif not isinstance(envelope_id, EnvelopeId):
            response.reason = "400 Bad request [invalid seq]"
            response.status_code = 400
        else:
            response.status_code = 200
        return response

    def stubbed_post_response(self, envelope: Envelope = None) -> Response:
        response = Response()

        if not envelope:
            response.reason = "400 No file uploaded"
            response.status_code = 400
        else:
            response.status_code = 200
            response.reason = "200 OK File uploaded"
        return response

    def get_envelope_staging(self, envelope_id: EnvelopeId = None) -> Response:
        """Get envelope from Tariff API staging environment."""
        return self.stubbed_get_response(envelope_id=envelope_id)

    def get_envelope_production(self, envelope_id: EnvelopeId = None) -> Response:
        """Get envelope from Tariff API production environment."""
        return self.stubbed_get_response(envelope_id=envelope_id)

    def post_envelope_staging(self, envelope: Envelope = None) -> Response:
        """Upload envelope to Tariff API staging environment."""
        return self.stubbed_post_response(envelope=envelope)

    def post_envelope_production(self, envelope: Envelope = None) -> Response:
        """Upload envelope to Tariff API production environment."""
        return self.stubbed_post_response(envelope=envelope)


class TariffAPI(TariffAPIBase):
    def __init__(self):
        super().__init__()
        self.client = TariffAPIClient()

    def get_envelope_staging(self, envelope_id: EnvelopeId) -> Response:
        """Get envelope from Tariff API staging environment."""
        return self.client.get_envelope_staging(envelope_id=envelope_id)

    def get_envelope_production(self, envelope_id: EnvelopeId) -> Response:
        """Get envelope from Tariff API production environment."""
        return self.client.get_envelope_production(envelope_id=envelope_id)

    def post_envelope_staging(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API staging environment."""
        return self.client.post_envelope_staging(envelope=envelope)

    def post_envelope_production(self, envelope: Envelope) -> Response:
        """Upload envelope to Tariff API production environment."""
        return self.client.post_envelope_production(envelope=envelope)
