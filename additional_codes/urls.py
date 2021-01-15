from django.urls import include
from django.urls import path
from rest_framework import routers

from additional_codes import views


api_router = routers.DefaultRouter()
api_router.register(r"additional_codes", views.AdditionalCodeViewSet)
api_router.register(r"additional_code_types", views.AdditionalCodeTypeViewSet)

urlpatterns = [
    path(
        "additional_codes/",
        views.AdditionalCodeList.as_view(),
        name="additional_code-ui-list",
    ),
    path("api/", include(api_router.urls)),
]
