from django.urls import path

import reports.utils as utils
from reports import views

app_name = "reports"

urlpatterns = [
    path("reports/", views.index, name="index"),
    path(
        "reports/<str:report_slug>/export-to-csv",
        views.export_report_to_csv,
        name="export_report_to_csv",
    ),
    path(
        "reports/<str:report_slug>/export-to-excel",
        views.export_report_to_excel,
        name="export_report_to_excel",
    ),
    path(
        "reports/<str:report_slug>/<str:current_tab>/export-report-with-tabs-to-csv/",
        views.export_report_to_csv,
        name="export_report_with_tabs_to_csv",
    ),
    path(
        "reports/upload_csv",
        views.upload_report_csv,
        name="upload_report_csv",
    ),
]

for report in utils.get_reports():
    urlpatterns.append(
        path(f"reports/{report.slug()}", views.report, name=report.slug()),
    )
