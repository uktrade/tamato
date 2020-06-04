from django.urls import include
from django.urls import path
from rest_framework import routers

from regulations import views


api_router = routers.DefaultRouter()
api_router.register(r"regulations", views.RegulationViewSet)

ui_router = routers.DefaultRouter()
ui_router.register(r"regulations", views.RegulationUIViewSet, basename="regulation-ui")

urlpatterns = [
    path("", include(ui_router.urls)),
    path("api/", include(api_router.urls)),
]
