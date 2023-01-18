from django.contrib import admin

from publishing.models import Envelope
from publishing.models import OperationalStatus


class EnvelopeAdmin(admin.ModelAdmin):
    ordering = ["-pk"]

    def has_delete_permission(self, request, obj=None):
        return True


class OperationalStatusAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "queue_state",
        "created_by",
        "created_at",
    )
    ordering = ["-pk"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(OperationalStatus, OperationalStatusAdmin)

admin.site.register(Envelope, EnvelopeAdmin)
