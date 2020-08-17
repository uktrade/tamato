from django.urls import include
from django.urls import path
from rest_framework import routers

from quotas import views


api_router = routers.DefaultRouter()
api_router.register(r"quota_order_numbers", views.QuotaOrderNumberViewset)
api_router.register(r"quota_order_number_origins", views.QuotaOrderNumberOriginViewset)
api_router.register(
    r"quota_order_number_origin_exclusions",
    views.QuotaOrderNumberOriginExclusionViewset,
)
api_router.register(r"quota_definitions", views.QuotaDefinitionViewset)
api_router.register(r"quota_associations", views.QuotaAssociationViewset)
api_router.register(r"quota_suspensions", views.QuotaSuspensionViewset)
api_router.register(r"quota_blocking_periods", views.QuotaBlockingViewset)
api_router.register(r"quota_events", views.QuotaEventViewset)

urlpatterns = [
    path("api/", include(api_router.urls)),
]
