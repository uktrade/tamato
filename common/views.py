import django.contrib.auth.views
from django.shortcuts import render

from workbaskets.models import WorkBasket


def index(request):
    workbaskets = []
    if request.user.is_authenticated:
        workbaskets = WorkBasket.objects.filter(author=request.user)
    return render(request, "common/index.jinja", context={"workbaskets": workbaskets,})


class LoginView(django.contrib.auth.views.LoginView):
    template_name = "common/login.jinja"


class LogoutView(django.contrib.auth.views.LogoutView):
    template_name = "common/logged_out.jinja"
