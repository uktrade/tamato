from django.urls import include
from django.urls import path
from django.urls import register_converter
from rest_framework import routers

from certificates import views
from certificates.path_converters import CertificateSIDConverter
from certificates.path_converters import CertificateTypeSIDConverter

register_converter(CertificateSIDConverter, "cert_sid")
register_converter(CertificateTypeSIDConverter, "ctype_sid")

api_router = routers.DefaultRouter()
api_router.register(r"certificates", views.CertificatesViewSet)
api_router.register(r"certificate_types", views.CertificateTypeViewSet)

detail = "<ctype_sid:certificate_type__sid><cert_sid:sid>"
description_detail = "<ctype_sid:described_certificate__certificate_type__sid><cert_sid:described_certificate__sid>/description/<sid:sid>"

ui_patterns = [
    path(
        "",
        views.CertificatesList.as_view(),
        name="certificate-ui-list",
    ),
    path(
        f"{detail}/",
        views.CertificateDetail.as_view(),
        name="certificate-ui-detail",
    ),
    path(
        f"{detail}/create-description/",
        views.CertificateCreateDescription.as_view(),
        name="certificate-ui-create-description",
    ),
    path(
        f"{description_detail}/edit/",
        views.CertificateUpdateDescription.as_view(),
        name="certificate_description-ui-edit",
    ),
    path(
        f"{description_detail}/confirm-create/",
        views.CertificateDescriptionConfirmCreate.as_view(),
        name="certificate_description-ui-confirm-create",
    ),
    path(
        f"{description_detail}/confirm-update/",
        views.CertificateDescriptionConfirmUpdate.as_view(),
        name="certificate_description-ui-confirm-update",
    ),
    path(
        f"{detail}/edit/",
        views.CertificateUpdate.as_view(),
        name="certificate-ui-edit",
    ),
    path(
        f"{detail}/confirm-update/",
        views.CertificateConfirmUpdate.as_view(),
        name="certificate-ui-confirm-update",
    ),
]

urlpatterns = [
    path("certificates/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
