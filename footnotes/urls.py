from django.urls import include
from django.urls import path
from rest_framework import routers

from footnotes import views


class APIRouter(routers.DefaultRouter):
    def get_default_basename(self, viewset):
        return f"api-{super().get_default_basename(viewset)}"


api_router = APIRouter()
api_router.register(r"footnotes", views.FootnoteViewSet)
api_router.register(r"footnote-types", views.FootnoteTypeViewSet)


ui_router = routers.DefaultRouter()
ui_router.register(r"footnotes", views.FootnoteUIViewSet)


urlpatterns = [
    path("", include(ui_router.urls)),
    path("api/", include(api_router.urls)),
]
