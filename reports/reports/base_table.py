from abc import abstractmethod

from reports.reports.base import ReportBase


class ReportBaseTable(ReportBase):
    name = "Base Table Report"
    report_template = "table"

    def __init__(self):
        pass

    @abstractmethod
    def query(self):
        pass

    @abstractmethod
    def headers(self) -> [dict]:
        pass

    @abstractmethod
    def rows(self) -> [[dict]]:
        pass

    @abstractmethod
    def row(self, row) -> [dict]:
        pass
