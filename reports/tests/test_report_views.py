# Create your tests here.
import pytest
from django.urls import reverse
from django.test import RequestFactory

from reports.utils import get_reports
from reports.views import export_report_to_csv
from reports.reports.expiring_quotas_with_no_definition_period import Report

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
        report_slug = "blank_goods_nomenclature_descriptions"

        response = export_report_to_csv(request, report_slug)

        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert (
            response["Content-Disposition"]
            == f'attachment; filename="{report_slug}_report.csv"'
        )

    def test_export_report_invalid_tab(self):
        request = RequestFactory().get("/")
        report_slug = Report.slug()
        invalid_tab = "Invalid tab"

        with pytest.raises(
            ValueError, match=f"Invalid current_tab value: {invalid_tab}"
        ):
            export_report_to_csv(request, report_slug, current_tab=invalid_tab)
