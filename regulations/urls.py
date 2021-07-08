from django.urls import include
from django.urls import path
from django.urls import register_converter
from rest_framework import routers

from regulations import views
from regulations.path_converters import RegulationIdConverter
from regulations.path_converters import RegulationRoleTypeConverter

register_converter(RegulationIdConverter, "reg_id")
register_converter(RegulationRoleTypeConverter, "reg_type")

api_router = routers.DefaultRouter()
api_router.register(r"regulations", views.RegulationViewSet)

detail = "<reg_type:role_type>/<reg_id:regulation_id>"

ui_patterns = [
    path(
        "",
        views.RegulationList.as_view(),
        name="regulation-ui-list",
    ),
    path(
        "create/",
        views.RegulationCreate.as_view(),
        name="regulation-ui-create",
    ),
    path(
        f"{detail}/confirm-create/",
        views.RegulationConfirmCreate.as_view(),
        name="regulation-ui-confirm-create",
    ),
    path(
        f"{detail}/",
        views.RegulationDetail.as_view(),
        name="regulation-ui-detail",
    ),
]

urlpatterns = [
    path("regulations/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
