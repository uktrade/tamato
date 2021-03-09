from django.urls import include
from django.urls import path
from django.urls import re_path
from rest_framework import routers

from regulations import views

api_router = routers.DefaultRouter()
api_router.register(r"regulations", views.RegulationViewSet)

ui_patterns = [
    path(
        "",
        views.RegulationList.as_view(),
        name="regulation-ui-list",
    ),
    re_path(
        r"(?P<role_type>\w+)/(?P<regulation_id>\w+)$",
        views.RegulationDetail.as_view(),
        name="regulation-ui-detail",
    ),
]

urlpatterns = [
    path("regulations/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
