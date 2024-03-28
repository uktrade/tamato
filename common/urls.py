"""
Common URLs.

Adds routes for views that are not specific to any part of the tariff, eg the
home page and user login
"""

from django.urls import include
from django.urls import path
from django.urls import register_converter

from common import views
from common.path_converters import NumericSIDConverter
from measures import views as measure_views

register_converter(NumericSIDConverter, "sid")

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("search/", views.SearchPageView.as_view(), name="search-page"),
    path("resources/", views.ResourcesView.as_view(), name="resources"),
    path("healthcheck", views.healthcheck, name="healthcheck"),
    path("app-info", views.AppInfoView.as_view(), name="app-info"),
    path(
        "duties/",
        measure_views.DutySentenceReference.as_view(),
        name="duties",
    ),
    path(
        "accessibility-statement",
        views.AccessibilityStatementView.as_view(),
        name="accessibility-statement",
    ),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("api-auth/", include("rest_framework.urls")),
    path("maintenance/", views.MaintenanceView.as_view(), name="maintenance"),
]
