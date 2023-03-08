from quotas.models import QuotaOrderNumber
from reports.reports.base_table import ReportBaseTable


class Report(ReportBaseTable):
    name = "Table report example accessing TAP data"
    enabled = False

    def headers(self) -> [dict]:
        return [
            {"text": "order number"},
            {"text": "start date"},
            {"text": "end date"},
        ]

    def row(self, row: QuotaOrderNumber) -> [dict]:
        return [
            {"text": row.order_number},
            {"text": row.valid_between.lower},
            {"text": row.valid_between.upper},
        ]

    def rows(self) -> [[dict]]:
        table_rows = []
        for row in self.query():
            table_rows.append(self.row(row))

        return table_rows

    def query(self):
        return QuotaOrderNumber.objects.latest_approved().filter(order_number="058005")
