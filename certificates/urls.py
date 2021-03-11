from django.urls import include
from django.urls import path
from django.urls import re_path
from rest_framework import routers

from certificates import views
from certificates.validators import CERTIFICATE_SID_REGEX
from certificates.validators import CERTIFICATE_TYPE_SID_REGEX

api_router = routers.DefaultRouter()
api_router.register(r"certificates", views.CertificatesViewSet)
api_router.register(r"certificate_types", views.CertificateTypeViewSet)

detail = fr"(?P<certificate_type__sid>{CERTIFICATE_TYPE_SID_REGEX[1:-1]})(?P<sid>{CERTIFICATE_SID_REGEX[1:-1]})"

ui_patterns = [
    path(
        "",
        views.CertificatesList.as_view(),
        name="certificate-ui-list",
    ),
    re_path(
        fr"{detail}/$",
        views.CertificateDetail.as_view(),
        name="certificate-ui-detail",
    ),
    re_path(
        fr"{detail}/edit/$",
        views.CertificateUpdate.as_view(),
        name="certificate-ui-edit",
    ),
    re_path(
        fr"{detail}/confirm-update/$",
        views.CertificateConfirmUpdate.as_view(),
        name="certificate-ui-confirm-update",
    ),
]

urlpatterns = [
    path("certificates/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
