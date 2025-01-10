from django.conf import settings
from django.middleware.security import SecurityMiddleware
from django.shortcuts import redirect
from django.urls import reverse


class MaintenanceModeMiddleware:
    """If MAINTENANCE_MODE env variable is True, reroute all user requests to
    MaintenanceModeView."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.MAINTENANCE_MODE and request.path_info != reverse("maintenance"):
            return redirect(reverse("maintenance"))

        response = self.get_response(request)
        return response


class CustomSecurityMiddleware(SecurityMiddleware):
    """Extends the security middleware to include the X-Permitted-Cross-Domain-
    Policies HTTP response header."""

    def process_response(self, request, response):
        response = super().process_response(request, response)
        response["X-Permitted-Cross-Domain-Policies"] = "none"
        return response
