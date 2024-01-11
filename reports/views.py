import csv

from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import render

import reports.reports.index as index_model

# Create your views here.
import reports.utils as utils


@permission_required("reports.view_report_index")
def index(request):
    context = {
        "report": index_model.IndexTable(),
    }

    return render(request, "reports/index.jinja", context)


@permission_required("reports.view_report")
def report(request):
    # find the report based on the request
    report_class = utils.get_report_by_slug(request.resolver_match.url_name)

    context = {
        "report": report_class(),
    }

    return render(
        request,
        utils.get_template_by_type(report_class.report_template),
        context,
    )


def export_report_to_csv(request, report_slug):
    report_class = utils.get_report_by_slug(report_slug)
    report_instance = report_class()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{report_slug}_report.csv"'

    writer = csv.writer(response)

    # Check if the report is a table or a chart
    if hasattr(report_instance, "headers"):
        # For table reports
        writer.writerow([header["text"] for header in report_instance.headers()])
        for row in report_instance.rows():
            writer.writerow([column["text"] for column in row])
    else:
        # For chart reports
        writer.writerow(["Label", "Data"])
        for label, data in zip(report_instance.labels(), report_instance.data()):
            writer.writerow([label, data])

    return response
