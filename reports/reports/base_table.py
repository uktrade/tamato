from abc import abstractmethod

from reports.reports.base import ReportBase


class ReportBaseTable(ReportBase):
    name = "Base Table Report"
    report_template = "table"
    tabular_reports = False

    def __init__(self):
        pass

    @abstractmethod
    def query(self):
        pass

    @abstractmethod
    def headers(self) -> [dict]:
        pass

    @abstractmethod
    def rows(self) -> [dict]:
        pass

    @abstractmethod
    def row(self, row) -> [dict]:
        pass

    def headers2(self) -> [dict]:
        return []

    def rows2(self) -> [dict]:
        return []

    def row2(self, row) -> [dict]:
        return []

    def headers3(self) -> [dict]:
        return []

    def rows3(self) -> [dict]:
        return []

    def row3(self, row) -> [dict]:
        return []

    def headers4(self) -> [dict]:
        return []

    def rows4(self) -> [dict]:
        return []

    def row4(self, row) -> [dict]:
        return []

    def query3(self):
        return []

    def query4(self):
        return []
