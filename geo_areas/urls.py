from django.urls import include
from django.urls import path
from rest_framework import routers

from geo_areas import views


api_router = routers.DefaultRouter()
api_router.register(r"geographical_areas", views.GeoAreaViewSet, basename="geoarea")

ui_router = routers.DefaultRouter()
ui_router.register(r"geographical_areas", views.GeoAreaUIViewSet, basename="geoarea-ui")

urlpatterns = [
    path("", include(ui_router.urls)),
    path("api/", include(api_router.urls)),
]
