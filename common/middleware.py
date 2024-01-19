from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class MaintenanceModeMiddleware:
    """If MAINTENANCE_MODE env variable is True, reroute all user requests to
    MaintenanceModeView."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.MAINTENANCE_MODE:
            return redirect(reverse("middleware"))

        response = self.get_response(request)
        return response
