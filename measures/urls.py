from django.urls import include
from django.urls import path
from django.urls import re_path

from measures import views

ui_patterns = [
    path(
        "",
        views.MeasureList.as_view(),
        name="measure-ui-list",
    ),
    re_path(
        r"^(?P<sid>\d*)$",
        views.MeasureDetail.as_view(),
        name="measure-ui-detail",
    ),
]


urlpatterns = [
    path("measures/", include(ui_patterns)),
]
