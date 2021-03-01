from django.urls import include
from django.urls import path

from measures import views

ui_patterns = [
    path(
        "",
        views.MeasureList.as_view(),
        name="measure-ui-list",
    ),
]


urlpatterns = [
    path("measures/", include(ui_patterns)),
]
