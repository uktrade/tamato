# Create your tests here.
import pytest
from django.urls import reverse
from django.utils.safestring import SafeString

from common.tests import factories
from reports.reports.base import ReportBase
from reports.reports.base_table import ReportBaseTable
from reports.reports.blank_goods_nomenclature_descriptions import Report
from reports.utils import get_child_classes
from reports.utils import get_report_by_slug
from reports.utils import get_reports
from reports.utils import get_template_by_type


class TestUtils:
    def test_get_child_classes(self):
        actual = get_child_classes(ReportBase)

        assert ReportBaseTable in actual

    def test_get_child_classes_v2(self):
        actual = get_child_classes(ReportBaseTable)

        assert Report in actual

    def test_get_reports(self):
        actual = get_reports()

        assert Report in actual

    def test_get_report_by_slug(self):
        actual = get_report_by_slug(Report.slug())
        expected = Report

        assert actual == expected

    def test_get_report_by_slug_no_match(self):
        actual = get_report_by_slug("yazooo")
        expected = None

        assert actual == expected

    def test_get_template_by_type(self):
        assert get_template_by_type("table") == "reports/report_table.jinja"
        assert get_template_by_type("chart") == "reports/report_chart.jinja"
        assert get_template_by_type("text") == "reports/report_text.jinja"
        with pytest.raises(Exception) as ex:
            get_template_by_type("werwer")
            assert str(ex) == "Unknown chart type : werwer"

    @pytest.mark.django_db
    def test_link_renderer_for_quotas(self, db):
        order_number_obj = factories.QuotaOrderNumberFactory.create()

        report_instance = Report()

        # Test without fragment
        result = report_instance.link_renderer_for_quotas(order_number_obj, "Test Text")
        expected_url = reverse("quota-ui-detail", args=[order_number_obj.sid])
        expected_output = f"<a class='govuk-link govuk-!-font-weight-bold' href='{expected_url}'>Test Text</a>"
        assert result == SafeString(expected_output)

        # Test with fragment
        result = report_instance.link_renderer_for_quotas(
            order_number_obj,
            "Test Text",
            fragment="#blocking-periods",
        )
        expected_url = (
            reverse("quota-ui-detail", args=[order_number_obj.sid])
            + "#blocking-periods"
        )
        expected_output = f"<a class='govuk-link govuk-!-font-weight-bold' href='{expected_url}'>Test Text</a>"
        assert result == SafeString(expected_output)
