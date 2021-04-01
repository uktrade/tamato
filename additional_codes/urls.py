from django.urls import include
from django.urls import path
from django.urls import re_path
from rest_framework import routers

from additional_codes import views
from common.urls import DESCRIPTION_ID_PATTERN

api_router = routers.DefaultRouter()
api_router.register(r"additional_codes", views.AdditionalCodeViewSet)
api_router.register(r"additional_code_types", views.AdditionalCodeTypeViewSet)

detail = r"^(?P<sid>\d*)"
description_detail = r"^(?P<described_additional_code__sid>\d*)"

ui_patterns = [
    path(
        "",
        views.AdditionalCodeList.as_view(),
        name="additional_code-ui-list",
    ),
    re_path(
        fr"{detail}/$",
        views.AdditionalCodeDetail.as_view(),
        name="additional_code-ui-detail",
    ),
    re_path(
        fr"{detail}/edit/$",
        views.AdditionalCodeUpdate.as_view(),
        name="additional_code-ui-edit",
    ),
    re_path(
        fr"{detail}/confirm-update/$",
        views.AdditionalCodeConfirmUpdate.as_view(),
        name="additional_code-ui-confirm-update",
    ),
    re_path(
        fr"{description_detail}/description/{DESCRIPTION_ID_PATTERN}/edit/$",
        views.AdditionalCodeUpdateDescription.as_view(),
        name="additional_code_description-ui-edit",
    ),
    re_path(
        fr"{description_detail}/description/{DESCRIPTION_ID_PATTERN}/confirm-update/$",
        views.AdditionalCodeDescriptionConfirmUpdate.as_view(),
        name="additional_code_description-ui-confirm-update",
    ),
]


urlpatterns = [
    path("additional_codes/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
