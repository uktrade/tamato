from django.contrib import admin

from notifications.forms import NotifiedUserAdminForm
from notifications.models import NotificationLog
from notifications.models import NotifiedUser


class NotifiedUserAdmin(admin.ModelAdmin):
    form = NotifiedUserAdminForm

    ordering = ["email"]
    list_display = (
        "email",
        "enrol_packaging",
    )
    actions = ["set_enrol_packaging", "unset_enrol_packaging"]

    def set_enrol_packaging(self, request, queryset):
        queryset.update(enrol_packaging=True)

    def unset_enrol_packaging(self, request, queryset):
        queryset.update(enrol_packaging=False)


class NotificationLogAdmin(admin.ModelAdmin):
    """Class providing read-only list and detail views for notification logs."""

    readonly_fields = []

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields) + [field.name for field in obj._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_save_and_continue"] = False
        extra_context["show_save"] = False
        return super(NotificationLogAdmin, self).changeform_view(
            request,
            object_id,
            extra_context=extra_context,
        )


admin.site.register(NotifiedUser, NotifiedUserAdmin)
admin.site.register(NotificationLog, NotificationLogAdmin)
