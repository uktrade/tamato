from django.urls import include
from django.urls import path
from rest_framework import routers

from footnotes import views


api_router = routers.DefaultRouter()
api_router.register(r"footnotes", views.FootnoteViewSet)

ui_router = routers.DefaultRouter()
ui_router.register(r"footnotes", views.FootnoteUIViewSet, basename="footnote-ui")

urlpatterns = [
    path("", include(ui_router.urls)),
    path("api/", include(api_router.urls)),
]
