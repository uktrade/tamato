from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from common.tests.factories import ImportBatchFactory
from tasks.models import StateChoices

pytestmark = pytest.mark.django_db


def test_automation_commodity_import_create_view_get(
    import_goods_automation_state_is_CAN_RUN,
    valid_user_client,
):
    """Test HTTP GET requests against AutomationCommodityImportCreateView."""
    url = reverse(
        "comodity-importer-automation-ui-create",
        kwargs={"pk": import_goods_automation_state_is_CAN_RUN.pk},
    )
    response = valid_user_client.get(url)
    assert response.status_code == 200
    assert import_goods_automation_state_is_CAN_RUN.get_state() == StateChoices.CAN_RUN


@patch("importer.forms.AutomationCommodityImportForm.save")
def test_automation_commodity_import_create_view_post(
    mock_save,
    import_goods_automation_state_is_CAN_RUN,
    valid_user_client,
    test_files_path,
):
    """Test HTTP POST requests against AutomationCommodityImportCreateView."""
    mock_save.return_value = ImportBatchFactory.create()
    with open(f"{test_files_path}/TGB12345.xml", "rb") as f:
        content = f.read()
    url = reverse(
        "comodity-importer-automation-ui-create",
        kwargs={"pk": import_goods_automation_state_is_CAN_RUN.pk},
    )
    data = {
        "taric_file": SimpleUploadedFile(
            "TGB12345.xml",
            content,
            content_type="text/xml",
        ),
    }
    response = valid_user_client.post(url, data)
    assert response.status_code == 302
    import_goods_automation_state_is_CAN_RUN.refresh_from_db()
    assert import_goods_automation_state_is_CAN_RUN.get_state() == StateChoices.RUNNING
