from django.conf import settings
from django.contrib import admin
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


class TamatoAdminSite(admin.AdminSite):
    @method_decorator(never_cache)
    def login(self, request, extra_context=None):
        if settings.SSO_ENABLED:
            raise Http404()
        return super().login(request=request, extra_context=extra_context)
