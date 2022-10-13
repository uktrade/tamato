from reports.reports.base_chart import ReportBaseChart


class Report(ReportBaseChart):
    name = "Chart example report with mock data"
    chart_type = "bar"

    def data(self):
        return [120, 33, 74, 55, 9]

    def labels(self):
        return ["One", "Two", "three", "Four", "Five"]

    def query(self):
        return []
