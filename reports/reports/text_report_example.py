from reports.reports.base_text import ReportBaseText


class Report(ReportBaseText):
    name = "Basic text report example"
    enabled = False

    def text(self) -> str:
        return "some text generated from the report class"
