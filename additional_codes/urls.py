from django.urls import include
from django.urls import path
from rest_framework import routers

from additional_codes import views
from common.paths import get_ui_paths

api_router = routers.DefaultRouter()
api_router.register(
    r"additional_codes",
    views.AdditionalCodeViewSet,
    basename="additionalcode",
)
api_router.register(r"additional_code_types", views.AdditionalCodeTypeViewSet)

detail = "<sid:sid>"
description_detail = "<sid:described_additionalcode__sid>/description/<sid:sid>"
ui_patterns = get_ui_paths(views, detail, description=description_detail)


urlpatterns = [
    path("additional_codes/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
