"""
Common URLs.

Adds routes for views that are not specific to any part of the tariff, eg the
home page and user login
"""

from django.urls import include
from django.urls import path
from django.urls import register_converter

from common.path_converters import NumericSIDConverter
from common.views import pages
from measures import views as measure_views

register_converter(NumericSIDConverter, "sid")

urlpatterns = [
    path("", pages.HomeView.as_view(), name="home"),
    path("search/", pages.SearchPageView.as_view(), name="search-page"),
    path("resources/", pages.ResourcesView.as_view(), name="resources"),
    path("pingdom/ping.xml", pages.HealthCheckView.as_view(), name="healthcheck"),
    path("app-info", pages.AppInfoView.as_view(), name="app-info"),
    path(
        "duties/",
        measure_views.DutySentenceReference.as_view(),
        name="duties",
    ),
    path(
        "accessibility-statement",
        pages.AccessibilityStatementView.as_view(),
        name="accessibility-statement",
    ),
    path("login", pages.LoginView.as_view(), name="login"),
    path("logout", pages.LogoutView.as_view(), name="logout"),
    path("api-auth/", include("rest_framework.urls")),
    path("maintenance/", pages.MaintenanceView.as_view(), name="maintenance"),
]
