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
    def rows(self) -> [[dict]]:
        pass

    @abstractmethod
    def row(self, row) -> [dict]:
        pass

    @abstractmethod
    def query2(self):
        pass

    @abstractmethod
    def headers2(self) -> [dict]:
        pass

    @abstractmethod
    def rows2(self) -> [[dict]]:
        pass

    @abstractmethod
    def row2(self, row) -> [dict]:
        pass
    
    @abstractmethod
    def query3(self):
        pass

    @abstractmethod
    def headers3(self) -> [dict]:
        pass

    @abstractmethod
    def rows3(self) -> [[dict]]:
        pass

    @abstractmethod
    def row3(self, row) -> [dict]:
        pass

    @abstractmethod
    def query4(self):
        pass

    @abstractmethod
    def headers4(self) -> [dict]:
        pass

    @abstractmethod
    def rows4(self) -> [[dict]]:
        pass

    @abstractmethod
    def row4(self, row) -> [dict]:
        pass