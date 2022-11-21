from django.urls import include
from django.urls import path
from django.urls import register_converter
from rest_framework import routers

from certificates import views
from certificates.path_converters import CertificateSIDConverter
from certificates.path_converters import CertificateTypeSIDConverter
from common.paths import get_ui_paths

register_converter(CertificateSIDConverter, "cert_sid")
register_converter(CertificateTypeSIDConverter, "ctype_sid")

api_router = routers.DefaultRouter()
api_router.register(
    r"certificates",
    views.CertificatesViewSet,
    basename="certificate",
)
api_router.register(
    r"certificate_types",
    views.CertificateTypeViewSet,
)

detail = "<ctype_sid:certificate_type__sid><cert_sid:sid>"
description_detail = "<ctype_sid:described_certificate__certificate_type__sid><cert_sid:described_certificate__sid>/description/<sid:sid>"
ui_patterns = get_ui_paths(views, detail, description=description_detail)

urlpatterns = [
    path("certificates/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
