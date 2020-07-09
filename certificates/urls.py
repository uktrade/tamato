from django.urls import include
from django.urls import path
from rest_framework import routers

from certificates import views


api_router = routers.DefaultRouter()
api_router.register(r"certificates", views.CertificatesViewSet)
api_router.register(r"certificate_types", views.CertificateTypeViewSet)

urlpatterns = [
    path("api/", include(api_router.urls)),
]
