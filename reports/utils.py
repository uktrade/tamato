from reports.reports import base


def get_child_classes(cls):
    child_classes = []
    for child in cls.__subclasses__():
        if child not in child_classes:
            child_classes.append(child)

    return child_classes


def get_reports():
    report_list = []

    for klass in get_child_classes(base.ReportBase):
        for subklass in get_child_classes(klass):
            report_list.append(subklass)

    return report_list


def get_report_by_slug(slug):
    reports = get_reports()
    for report in reports:
        if report.slug() == slug:
            return report

    return None


def get_template_by_type(template_type):
    known_template_types = ["text", "chart", "table"]

    if template_type in known_template_types:
        return f"reports/report_{template_type}.jinja"
    else:
        raise Exception(f"Unknown chart type : {template_type}")
