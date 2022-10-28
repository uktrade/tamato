# Create your tests here.
import pytest

from reports.reports.base import ReportBase
from reports.reports.base_chart import ReportBaseChart
from reports.reports.base_table import ReportBaseTable
from reports.reports.base_text import ReportBaseText
from reports.reports.blank_goods_nomenclature_descriptions import Report
from reports.reports.index import IndexTable


class TestBaseReport:
    def test_base_report_init_properties(self):
        target = ReportBase()

        name = "Base Report"
        report_details = "Please complete report details"
        report_template = "text"

        assert target.name == name
        assert target.report_details == report_details
        assert target.report_template == report_template

    def test_base_report_slug(self):
        target = ReportBase()

        expected = "base_report"

        assert target.slug() == expected

    @pytest.mark.parametrize(
        "name_string,expected_slug",
        [
            ("ALL-CAPS-NAME", "all_caps_name"),
            ("names    with    lots      of       spaces", "names_with_lots_of_spaces"),
            ("multiline example\nhere", "multiline_example_here"),
            (
                "non_alpha_chars!@#$%ˆ&*()_+-={}[]:\";;'bob the potato",
                "non_alpha_chars_bob_the_potato",
            ),
        ],
    )
    def test_base_report_slug_variations(self, name_string, expected_slug):
        class SlugTestReport(ReportBase):
            name = name_string

        expected = expected_slug

        assert SlugTestReport.slug() == expected


class TestBaseReportChildClasses:
    @pytest.mark.parametrize(
        "klass,name,report_template,chart_type",
        [
            (ReportBaseChart, "Base Chart Report", "chart", "pie"),
            (ReportBaseTable, "Base Table Report", "table", None),
            (ReportBaseText, "Base Text Report", "text", None),
        ],
    )
    def test_report_init_properties(self, klass, name, report_template, chart_type):
        class SlugTestReport(klass):
            def headers(self):
                pass

            def query(self):
                pass

            def row(self):
                pass

            def rows(self):
                pass

            def data(self):
                pass

            def labels(self):
                pass

            def text(self):
                pass

        target = SlugTestReport()

        assert target.name == name
        assert target.report_template == report_template

        if chart_type is not None:
            assert target.chart_type == chart_type

    @pytest.mark.parametrize(
        "klass,slug",
        [
            (ReportBaseChart, "base_chart_report"),
            (ReportBaseTable, "base_table_report"),
            (ReportBaseText, "base_text_report"),
        ],
    )
    def test_report_slug(self, klass, slug):
        class SlugTestReport(klass):
            def headers(self):
                pass

            def query(self):
                pass

            def row(self):
                pass

            def rows(self):
                pass

            def data(self):
                pass

            def labels(self):
                pass

            def text(self):
                pass

        target = SlugTestReport()

        assert target.slug() == slug


class TestIndex:
    def test_index_table_headers(self):
        target = IndexTable()

        assert len(target.headers()) == 2
        assert target.headers()[0]["text"] == "Name"
        assert target.headers()[1]["text"] == "Link"

    def test_index_table_rows(self):
        target = IndexTable()

        rows = target.rows()

        assert len(rows) > 0

    def test_index_table_row(self):
        target = IndexTable()

        row = target.row(Report)

        assert row[0]["text"] == "Blank Goods Nomenclature descriptions"
        assert row[1]["html"] == f'<a href="/reports/{Report.slug()}">View Report</a>'
