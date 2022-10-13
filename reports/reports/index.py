from reports import utils
from reports.reports.base import ReportBase


class IndexTable:
    def __init__(self):
        pass

    def headers(self) -> [dict]:
        return [{"text": "Name"}, {"text": "Link"}]

    def rows(self) -> [[dict]]:
        results = []

        for report in utils.get_reports():
            results.append(self.row(report))

        return results

    def row(self, row: ReportBase) -> [dict]:
        return [
            {"text": row.name},
            {"html": f'<a href="/reports/{row.slug()}">View Report</a>'},
        ]
