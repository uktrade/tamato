import json
import os
from unittest.mock import Mock

import dotenv
import pytest

from common.tests import factories
from hmrc_sdes.api_client import HmrcSdesClient


def test_sdes_client(responses, settings):
    settings.HMRC = {
        "client_id": "test",
        "client_secret": "test",
        "service_reference_number": "test-srn",
        "token_url": "https://test-api.service.hmrc.gov.uk/oauth/token",
    }

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
