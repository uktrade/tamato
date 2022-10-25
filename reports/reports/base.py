from abc import ABC

from django.utils.text import slugify


class ReportBase(ABC):
    name = "Base Report"
    report_details = "Please complete report details"
    report_template = "text"

    def __init__(self):
        pass

    @classmethod
    def slug(cls):
        result = slugify(cls.name).replace("-", "_")
        result = result.replace("__", "_")
        return result
