from django.urls import include
from django.urls import path

from measures import views

ui_patterns = [
    path(
        "",
        views.MeasureList.as_view(),
        name="measure-ui-list",
    ),
    path(
        "<sid:sid>/",
        views.MeasureDetail.as_view(),
        name="measure-ui-detail",
    ),
]


urlpatterns = [
    path("measures/", include(ui_patterns)),
]
