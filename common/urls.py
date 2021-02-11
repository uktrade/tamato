from django.urls import include
from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("healthcheck", views.healthcheck, name="healthcheck"),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("api-auth/", include("rest_framework.urls")),
]
