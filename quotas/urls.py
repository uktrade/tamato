from django.urls import include
from django.urls import path
from rest_framework import routers

from common.paths import get_ui_paths
from quotas import views

api_router = routers.DefaultRouter()
api_router.register(
    r"quota_order_numbers",
    views.QuotaOrderNumberViewset,
    basename="quotaordernumber",
)
api_router.register(
    r"quota_order_number_origins",
    views.QuotaOrderNumberOriginViewset,
)
api_router.register(
    r"quota_order_number_origin_exclusions",
    views.QuotaOrderNumberOriginExclusionViewset,
)
api_router.register(
    r"quota_definitions",
    views.QuotaDefinitionViewset,
)
api_router.register(
    r"quota_associations",
    views.QuotaAssociationViewset,
)
api_router.register(
    r"quota_suspensions",
    views.QuotaSuspensionViewset,
)
api_router.register(
    r"quota_blocking_periods",
    views.QuotaBlockingViewset,
)
api_router.register(
    r"quota_events",
    views.QuotaEventViewset,
)

ui_patterns = get_ui_paths(views, "<sid:sid>")

urlpatterns = [
    path("quotas/", include(ui_patterns)),
    path(
        f"quotas/<sid>/quota-definitions/",
        views.QuotaDefinitionList.as_view(),
        name="quota-definitions",
    ),
    path(
        f"quotas/<sid>/quota_definitions/confirm-delete/",
        views.QuotaDefinitionConfirmDelete.as_view(),
        name="quota_definition-ui-confirm-delete",
    ),
    path(
        f"quota_order_number_origins/<sid>/edit/",
        views.QuotaOrderNumberOriginUpdate.as_view(),
        name="quota_order_number_origin-ui-edit",
    ),
    path(
        f"quotas/<sid>/quota_order_number_origins/",
        views.QuotaOrderNumberOriginCreate.as_view(),
        name="quota_order_number_origin-ui-create",
    ),
    path(
        f"quota_order_number_origins/<sid>/confirm-create/",
        views.QuotaOrderNumberOriginConfirmCreate.as_view(),
        name="quota_order_number_origin-ui-confirm-create",
    ),
    path(
        f"quota_definitions/<sid>/edit/",
        views.QuotaDefinitionUpdate.as_view(),
        name="quota_definition-ui-edit",
    ),
    path(
        f"quota_definitions/<sid>/delete/",
        views.QuotaDefinitionDelete.as_view(),
        name="quota_definition-ui-delete",
    ),
    path(
        f"quota_definitions/<sid>/confirm-update/",
        views.QuotaDefinitionConfirmUpdate.as_view(),
        name="quota_definition-ui-confirm-update",
    ),
    path(
        f"quota_order_number_origins/<sid>/edit/",
        views.QuotaOrderNumberOriginUpdate.as_view(),
        name="quota_order_number_origin-ui-edit-update",
    ),
    path(
        f"quota_order_number_origins/<sid>/confirm-update/",
        views.QuotaOrderNumberOriginConfirmUpdate.as_view(),
        name="quota_order_number_origin-ui-confirm-update",
    ),
    path("api/", include(api_router.urls)),
]