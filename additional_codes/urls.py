from django.urls import include
from django.urls import path
from rest_framework import routers

from additional_codes import views
from common.paths import get_ui_paths_ext

api_router = routers.DefaultRouter()
api_router.register(
    r"additional_codes",
    views.AdditionalCodeViewSet,
    basename="additionalcode",
)
api_router.register(r"additional_code_types", views.AdditionalCodeTypeViewSet)


# Paths for AdditionalCode<action> views.
ui_patterns = get_ui_paths_ext(
    view_module=views,
    class_name_prefix="AdditionalCode",
    object_id_pattern="<sid:sid>",
    url_base="",
)
# Paths for AdditionalCodeDescription<action> views.
ui_patterns += get_ui_paths_ext(
    view_module=views,
    class_name_prefix="AdditionalCodeDescription",
    object_id_pattern="<sid:sid>",
    url_base="<sid:described_additionalcode__sid>/description/",
)

urlpatterns = [
    path("additional_codes/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
