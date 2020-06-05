from django.urls import include
from django.urls import path
from rest_framework import routers

from workbaskets import views


api_router = routers.DefaultRouter()
api_router.register(r"workbaskets", views.WorkBasketViewSet)

ui_router = routers.DefaultRouter()
ui_router.register(r"workbaskets", views.WorkBasketUIViewSet, basename="workbasket-ui")

urlpatterns = [
    path("", include(ui_router.urls)),
    path("api/", include(api_router.urls)),
]
