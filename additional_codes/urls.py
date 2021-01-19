from django.urls import include
from django.urls import path
from django.urls import re_path
from rest_framework import routers

from additional_codes import views

api_router = routers.DefaultRouter()
api_router.register(r"additional_codes", views.AdditionalCodeViewSet)
api_router.register(r"additional_code_types", views.AdditionalCodeTypeViewSet)

ui_patterns = [
    path(
        "",
        views.AdditionalCodeList.as_view(),
        name="additional_code-ui-list",
    ),
    re_path(
        r"^(?P<sid>\d*)$",
        views.AdditionalCodeDetail.as_view(),
        name="additional_code-ui-detail",
    ),
]


urlpatterns = [
    path("additional_codes/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
