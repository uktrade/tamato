from django.urls import include
from django.urls import path
from django.urls import register_converter
from rest_framework import routers

from common.paths import get_ui_paths
from footnotes import views
from footnotes.path_converters import FootnoteIdConverter
from footnotes.path_converters import FootnoteTypeIdConverter

register_converter(FootnoteIdConverter, "footnote_id")
register_converter(FootnoteTypeIdConverter, "footnote_type_id")

api_router = routers.DefaultRouter()
api_router.register(
    r"footnotes",
    views.FootnoteViewSet,
    basename="footnote",
)
api_router.register(
    r"footnote_types",
    views.FootnoteTypeViewSet,
    basename="footnotetype",
)

detail = "<footnote_type_id:footnote_type__footnote_type_id><footnote_id:footnote_id>"
description_detail = "<footnote_type_id:described_footnote__footnote_type__footnote_type_id><footnote_id:described_footnote__footnote_id>/description/<sid:sid>"
ui_patterns = get_ui_paths(views, detail, description=description_detail)

urlpatterns = [
    path("footnotes/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
