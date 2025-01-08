from django.middleware.security import SecurityMiddleware


class CustomSecurityMiddleware(SecurityMiddleware):
    """Extends the security middleware to include the X-Permitted-Cross-Domain-
    Policies HTTP response header."""

    def process_response(self, request, response):
        response = super().process_response(request, response)
        response["X-Permitted-Cross-Domain-Policies"] = "none"
        return response
