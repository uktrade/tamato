# Create your tests here.
import pytest
from django.urls import reverse

from reports.utils import get_reports

pytestmark = pytest.mark.django_db


class TestReportViews:
    @pytest.mark.parametrize(
        "client_name,http_status",
        [
            ("client", 302),
            ("valid_user_client", 302),
            ("superuser_client", 200),
        ],
    )
    def test_index(self, client_name, http_status, request):
        client = request.getfixturevalue(client_name)
        response = client.get(reverse("reports:index"))
        assert response.status_code == http_status

    @pytest.mark.parametrize(
        "client_name,http_status",
        [
            ("client", 302),
            ("valid_user_client", 302),
            ("superuser_client", 200),
        ],
    )
    def test_all_report_unauthorised(self, client_name, http_status, request):
        client = request.getfixturevalue(client_name)
        reports = get_reports()

        for report in reports:
            response = client.get(reverse(f"reports:{report.slug()}"))
            assert response.status_code == http_status
