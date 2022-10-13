from abc import abstractmethod

from reports.reports.base import ReportBase


class ReportBaseText(ReportBase):
    name = "Base Text Report"
    report_template = "text"

    def __init__(self):
        pass

    @abstractmethod
    def text(self):
        return "Some text from query method"
