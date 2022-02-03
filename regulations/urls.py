from django.urls import include
from django.urls import path
from django.urls import register_converter
from rest_framework import routers

from common.paths import get_ui_paths
from regulations import views
from regulations.path_converters import RegulationIdConverter
from regulations.path_converters import RegulationRoleTypeConverter

register_converter(RegulationIdConverter, "reg_id")
register_converter(RegulationRoleTypeConverter, "reg_type")

api_router = routers.DefaultRouter()
api_router.register(r"regulations", views.RegulationViewSet, basename="regulation")

detail = "<reg_type:role_type>/<reg_id:regulation_id>"
ui_patterns = get_ui_paths(views, detail)

urlpatterns = [
    path("regulations/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
