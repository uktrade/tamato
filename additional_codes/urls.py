from django.urls import include
from django.urls import path
from rest_framework import routers

from additional_codes import views


api_router = routers.DefaultRouter()
api_router.register(r"additional_codes", views.AdditionalCodeViewSet)
api_router.register(r"additional_code_types", views.AdditionalCodeTypeViewSet)

ui_router = routers.DefaultRouter()
ui_router.register(
    r"additional_codes", views.AdditionalCodeUIViewSet, basename="additional_code-ui"
)

urlpatterns = [
    path("", include(ui_router.urls)),
    path("api/", include(api_router.urls)),
]
