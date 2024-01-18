from abc import ABC

from django.utils.text import slugify


class ReportBase(ABC):
    name = "Base Report"
    report_details = "Please complete report details"
    report_template = "text"
    description = "This report is pending a description"
    enabled = True

    def __init__(self):
        pass

    @classmethod
    def slug(cls):
        result = slugify(cls.name).replace("-", "_")
        result = result.replace("__", "_")
        return result

    @classmethod
    def slugify(tab_name):
        result = slugify(tab_name).replace("-", "_")
        result = result.lower()
        return result
