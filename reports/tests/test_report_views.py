# Create your tests here.
import pytest
from django.urls import reverse
from django.test import RequestFactory

from reports.utils import get_reports
from reports.views import export_report_to_csv

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

   
    def test_export_report_to_csv(self, request):
        request = RequestFactory().get("/")
        report_slug = (
            "cds_rejections_in_the_last_12_months"
        )

        response = export_report_to_csv(request, report_slug)

        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert (
            response["Content-Disposition"]
            == f'attachment; filename="{report_slug}_report.csv"'
        )
