from django.urls import include
from django.urls import path
from rest_framework import routers

from additional_codes import views

api_router = routers.DefaultRouter()
api_router.register(r"additional_codes", views.AdditionalCodeViewSet)
api_router.register(r"additional_code_types", views.AdditionalCodeTypeViewSet)

detail = "<sid:sid>"
description_detail = "<sid:described_additionalcode__sid>/description/<sid:sid>"

ui_patterns = [
    path(
        "",
        views.AdditionalCodeList.as_view(),
        name="additional_code-ui-list",
    ),
    path(
        f"{detail}/",
        views.AdditionalCodeDetail.as_view(),
        name="additional_code-ui-detail",
    ),
    path(
        f"{detail}/edit/",
        views.AdditionalCodeUpdate.as_view(),
        name="additional_code-ui-edit",
    ),
    path(
        f"{detail}/confirm-update/",
        views.AdditionalCodeConfirmUpdate.as_view(),
        name="additional_code-ui-confirm-update",
    ),
    path(
        f"{detail}/create-description/",
        views.AdditionalCodeCreateDescription.as_view(),
        name="additional_code-ui-create-description",
    ),
    path(
        f"{description_detail}/edit/",
        views.AdditionalCodeUpdateDescription.as_view(),
        name="additional_code_description-ui-edit",
    ),
    path(
        f"{description_detail}/confirm-create/",
        views.AdditionalCodeDescriptionConfirmCreate.as_view(),
        name="additional_code_description-ui-confirm-create",
    ),
    path(
        f"{description_detail}/confirm-update/",
        views.AdditionalCodeDescriptionConfirmUpdate.as_view(),
        name="additional_code_description-ui-confirm-update",
    ),
]


urlpatterns = [
    path("additional_codes/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
