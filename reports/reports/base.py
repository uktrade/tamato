from abc import ABC
from re import sub


class ReportBase(ABC):
    name = "Base Report"
    report_details = "Please complete report details"
    report_template = "text"

    def __init__(self):
        pass

    @classmethod
    def slug(cls):
        result = cls.name
        result = result.replace("\n", " ").replace("\r", " ")
        result = "_".join(
            sub(
                "([A-Z][a-z]+)",
                r" \1",
                sub("([A-Z]+)", r" \1", result.replace("-", " ")),
            ).split(),
        ).lower()
        return result
