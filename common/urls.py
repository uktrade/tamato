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

register_converter(NumericSIDConverter, "sid")

urlpatterns = [
    path("", views.DashboardView.as_view(), name="index"),
    path("my-workbasket/", views.MyWorkbasketView.as_view(), name="my-workbasket"),
    path("wbactions", views.WorkbasketActionView.as_view(), name="wbactions"),
    path("healthcheck", views.healthcheck, name="healthcheck"),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("api-auth/", include("rest_framework.urls")),
]
