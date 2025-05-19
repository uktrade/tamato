from open_data.models.report_models import ReportCommodityReport
from open_data.utils import get_report_timestamp_str
from reports.reports.base_text import ReportBaseText


class Report(ReportBaseText):
    name = "Commodities"
    description = (
        "The report is too large to display. Use 'Export to csv' to download it."
    )
    download_csv = True

    def text(self):
        return get_report_timestamp_str()

    def headers(self) -> [dict]:
        return [
            {"text": "Id"},
            {"text": "commodity__sid"},
            {"text": "commodity__code"},
            {"text": "commodity__suffix"},
            {"text": "commodity__description"},
            {"text": "commodity__validity_start"},
            {"text": "commodity__validity_end"},
            {"text": "parent__sid"},
            {"text": "parent__code"},
            {"text": "parent__suffix"},
        ]

    def row(self, row: ReportCommodityReport) -> [dict]:
        return [
            {"text": row.id},
            {"text": row.commodity_sid},
            {"text": row.commodity_code},
            {"text": row.commodity_suffix},
            {"text": row.commodity_description},
            {"text": row.commodity_validity_start},
            {"text": row.commodity_validity_end},
            {"text": row.parent_sid},
            {"text": row.parent_code},
            {"text": row.parent_suffix},
        ]

    def rows(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        return ReportCommodityReport.objects.all()
