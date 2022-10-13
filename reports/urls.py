from django.urls import path

import reports.utils as utils
from reports import views

urlpatterns = [
    path("reports/", views.index, name="reportsindex"),
]

for report in utils.get_reports():
    urlpatterns.append(
        path(f"reports/{report.slug()}", views.report, name=report.slug()),
    )
