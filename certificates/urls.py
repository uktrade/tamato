from django.urls import include
from django.urls import path
from django.urls import re_path
from rest_framework import routers

from certificates import views
from certificates.validators import CERTIFICATE_SID_REGEX

api_router = routers.DefaultRouter()
api_router.register(r"certificates", views.CertificatesViewSet)
api_router.register(r"certificate_types", views.CertificateTypeViewSet)

ui_patterns = [
    path(
        "",
        views.CertificatesList.as_view(),
        name="certificate-ui-list",
    ),
    re_path(
        fr"^(?P<sid>{CERTIFICATE_SID_REGEX[1:-1]})$",
        views.CertificateDetail.as_view(),
        name="certificate-ui-detail",
    ),
]

urlpatterns = [
    path("certificates/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
