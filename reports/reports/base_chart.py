from abc import abstractmethod

from reports.reports.base import ReportBase


class ReportBaseChart(ReportBase):
    name = "Base Chart Report"
    report_template = "chart"
    chart_type = "pie"

    def __init__(self):
        pass

    @abstractmethod
    def query(self):
        pass

    @abstractmethod
    def data(self):
        pass

    @abstractmethod
    def labels(self):
        pass
