from django.urls import include
from django.urls import path
from django.urls import re_path
from rest_framework import routers

from footnotes import views


api_router = routers.DefaultRouter()
api_router.register(r"footnotes", views.FootnoteViewSet)
api_router.register(r"footnote_types", views.FootnoteTypeViewSet)

footnote_detail = r"^footnotes/(?P<footnote_type__footnote_type_id>[A-Z]{2,3})(?P<footnote_id>[0-9]{3}|[0-9]{5})/"
footnote_description_detail = r"^footnotes/(?P<described_footnote__footnote_type__footnote_type_id>[A-Z]{2,3})(?P<described_footnote__footnote_id>[0-9]{3}|[0-9]{5})/"

urlpatterns = [
    path(
        "footnotes/",
        views.FootnoteList.as_view(),
        name="footnote-ui-list",
    ),
    re_path(
        (footnote_detail + r"$"),
        views.FootnoteDetail.as_view(),
        name="footnote-ui-detail",
    ),
    re_path(
        (footnote_detail + r"edit/$"),
        views.FootnoteUpdate.as_view(),
        name="footnote-ui-edit",
    ),
    re_path(
        (footnote_detail + r"confirm-update/$"),
        views.FootnoteConfirmUpdate.as_view(),
        name="footnote-ui-confirm-update",
    ),
    re_path(
        (
            footnote_description_detail
            + r"description/(?P<description_period_sid>[0-9]{1,8})/edit/$"
        ),
        views.FootnoteDescriptionUpdate.as_view(),
        name="footnote-ui-description-edit",
    ),
    re_path(
        (
            footnote_description_detail
            + r"description/(?P<description_period_sid>[0-9]{1,8})/confirm-update/$"
        ),
        views.FootnoteDescriptionConfirmUpdate.as_view(),
        name="footnote-ui-description-confirm-update",
    ),
    path("api/", include(api_router.urls)),
]
