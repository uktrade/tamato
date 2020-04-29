import django.contrib.auth.views
from django.shortcuts import render


def index(request):
    return render(request, "common/index.jinja")


class LoginView(django.contrib.auth.views.LoginView):
    template_name = "common/login.jinja"


class LogoutView(django.contrib.auth.views.LogoutView):
    template_name = "common/logged_out.jinja"
