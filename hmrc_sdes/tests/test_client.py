import json
import os
import uuid
from hashlib import md5
from unittest.mock import Mock

import dotenv
import pytest

from common.tests import factories
from hmrc_sdes.api_client import HmrcSdesClient


pytestmark = pytest.mark.django_db


def test_sdes_client(responses):
    responses.add(
        responses.POST,
        url="https://test-api.service.hmrc.gov.uk/oauth/token",
        json={
            "access_token": "access_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "refresh_token",
            "scope": "write:transfer-complete write:transfer-ready",
        },
    )
    client = HmrcSdesClient()

    assert len(responses.calls) == 1

    responses.add(
        responses.POST,
        url="https://test-api.service.hmrc.gov.uk/organisations/notification/files/transfer/ready/test-srn",
    )

    upload = factories.UploadFactory.build(
        correlation_id="test-correlation-id",
        file=Mock(size=1),
        checksum="test-checksum",
    )

    client.notify_transfer_ready(upload)

    request = responses.calls[1].request
    hmrc_json = "application/vnd.hmrc.1.0+json"

    assert request.headers["Accept"] == hmrc_json
    assert request.headers["Content-Type"] == f"{hmrc_json}; charset=UTF-8"

    assert json.loads(responses.calls[1].request.body) == {
        "informationType": "EDM",
        "correlationID": upload.correlation_id,
        "file": {
            "fileName": upload.filename,
            "fileSize": upload.file.size,
            "checksum": upload.checksum,
            "checksumAlgorithm": "MD5",
        },
    }


@pytest.mark.hmrc_live_api
def test_api_call(responses, settings):
    responses.add_passthru(settings.HMRC["base_url"])

    # reload settings from env, overriding test settings
    dotenv.read_dotenv(os.path.join(settings.BASE_DIR, ".env"))
    settings.HMRC["client_id"] = os.environ.get("HMRC_API_CLIENT_ID")
    settings.HMRC["client_secret"] = os.environ.get("HMRC_API_CLIENT_SECRET")
    settings.HMRC["service_reference_number"] = os.environ.get(
        "HMRC_API_SERVICE_REFERENCE_NUMBER"
    )

    # fetches OAuth2 access token on instantiation
    client = HmrcSdesClient()
    assert client.get_session().token is not None

    # check fraud prevention headers
    result = client.get(
        f"{client.base_url}/test/fraud-prevention-headers/validate",
    ).json()
    assert result.get("errors") is None

    # generate a dummy upload of an empty file with a valid checksum
    upload = factories.UploadFactory()
    upload.file = Mock(size=0)
    upload.checksum = md5("".encode("utf-8")).hexdigest()

    response = client.notify_transfer_ready(upload)
    assert response.status_code == 204  # no data on success
