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
    basename="quotaordernumberorigin",
)
api_router.register(
    r"quota_order_number_origin_exclusions",
    views.QuotaOrderNumberOriginExclusionViewset,
    basename="quotaordernumberoriginexclusion",
)
api_router.register(
    r"quota_definitions",
    views.QuotaDefinitionViewset,
    basename="quotadefinition",
)
api_router.register(
    r"quota_associations",
    views.QuotaAssociationViewset,
    basename="quotaassociation",
)
api_router.register(
    r"quota_suspensions",
    views.QuotaSuspensionViewset,
    basename="quotasuspension",
)
api_router.register(
    r"quota_blocking_periods",
    views.QuotaBlockingViewset,
    basename="quotablockingperiod",
)
api_router.register(
    r"quota_events",
    views.QuotaEventViewset,
    basename="quotaevent",
)

ui_patterns = get_ui_paths(views, "<sid:sid>")

urlpatterns = [
    path("quotas/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
