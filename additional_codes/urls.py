from django.urls import include
from django.urls import path
from django.urls import re_path
from rest_framework import routers

from additional_codes import views

additional_code_detail = r"^(?P<sid>\d*)/"

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
        (additional_code_detail + r"$"),
        views.AdditionalCodeDetail.as_view(),
        name="additional_code-ui-detail",
    ),
    re_path(
        (r"^(?P<description_period_sid>\d*)/edit/"),
        views.AdditionalCodeEditDescription.as_view(),
        name="additional_code-ui-edit-description",
    ),
    re_path(
        (r"^(?P<description_period_sid>\d*)/edit/confirm-update/"),
        views.AdditionalCodeConfirmDescriptionUpdate.as_view(),
        name="additional_code-confirm-description-update",
    ),
]


urlpatterns = [
    path("additional_codes/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
