from django.urls import path

import reports.utils as utils
from reports import views

app_name = "reports"

urlpatterns = [
    path("reports/", views.index, name="index"),
]

for report in utils.get_reports():
    urlpatterns.append(
        path(f"reports/{report.slug()}", views.report, name=report.slug()),
    )
