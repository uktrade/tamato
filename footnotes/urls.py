from django.urls import include
from django.urls import path
from django.urls import register_converter
from rest_framework import routers

from footnotes import views
from footnotes.path_converters import FootnoteIdConverter
from footnotes.path_converters import FootnoteTypeIdConverter

register_converter(FootnoteIdConverter, "footnote_id")
register_converter(FootnoteTypeIdConverter, "footnote_type_id")

api_router = routers.DefaultRouter()
api_router.register(r"footnotes", views.FootnoteViewSet)
api_router.register(r"footnote_types", views.FootnoteTypeViewSet)

detail = "<footnote_type_id:footnote_type__footnote_type_id><footnote_id:footnote_id>"
description_detail = "<footnote_type_id:described_footnote__footnote_type__footnote_type_id><footnote_id:described_footnote__footnote_id>/description/<sid:sid>"

ui_patterns = [
    path(
        "",
        views.FootnoteList.as_view(),
        name="footnote-ui-list",
    ),
    path(
        f"{detail}/",
        views.FootnoteDetail.as_view(),
        name="footnote-ui-detail",
    ),
    path(
        f"{detail}/edit/",
        views.FootnoteUpdate.as_view(),
        name="footnote-ui-edit",
    ),
    path(
        f"{detail}/confirm-update/",
        views.FootnoteConfirmUpdate.as_view(),
        name="footnote-ui-confirm-update",
    ),
    path(
        f"{description_detail}/edit/",
        views.FootnoteUpdateDescription.as_view(),
        name="footnote_description-ui-edit",
    ),
    path(
        f"{description_detail}/confirm-update/",
        views.FootnoteDescriptionConfirmUpdate.as_view(),
        name="footnote_description-ui-confirm-update",
    ),
    path("api/", include(api_router.urls)),
]

urlpatterns = [
    path("footnotes/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
