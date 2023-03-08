from django.contrib.auth.decorators import permission_required
from django.shortcuts import render

import reports.reports.index as index_model

# Create your views here.
import reports.utils as utils


@permission_required("app.view_report_index")
def index(request):
    context = {
        "report": index_model.IndexTable(),
    }

    return render(request, "reports/index.jinja", context)


@permission_required("app.view_report")
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
