from django.contrib import admin

from notifications.forms import NotifiedUserAdminForm
from notifications.models import Notification
from notifications.models import NotificationLog
from notifications.models import NotifiedUser


class NotifiedUserAdmin(admin.ModelAdmin):
    form = NotifiedUserAdminForm

    ordering = ["email"]
    list_display = (
        "email",
        "enrol_packaging",
        "enrol_api_publishing",
        "enrol_goods_report",
    )
    actions = [
        "set_enrol_packaging",
        "unset_enrol_packaging",
        "set_enrol_api_publishing",
        "unset_enrol_api_publishing",
        "set_enrol_goods_report",
        "unset_enrol_goods_report",
    ]

    def set_enrol_packaging(self, request, queryset):
        queryset.update(enrol_packaging=True)

    def unset_enrol_packaging(self, request, queryset):
        queryset.update(enrol_packaging=False)

    def set_enrol_api_publishing(self, request, queryset):
        queryset.update(enrol_api_publishing=True)

    def unset_enrol_api_publishing(self, request, queryset):
        queryset.update(enrol_api_publishing=False)

    def set_enrol_goods_report(self, request, queryset):
        queryset.update(enrol_goods_report=True)

    def unset_enrol_goods_report(self, request, queryset):
        queryset.update(enrol_goods_report=False)


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


class NotificationAdmin(admin.ModelAdmin):
    """Class providing read-only list and detail views for notification."""

    ordering = ["pk"]
    list_display = (
        "pk",
        "email_type",
        "display_users",
        "attachment_object",
    )

    readonly_fields = []

    def display_users(self, obj):
        return ", ".join(
            [user.email for user in obj.notified_users.all()],
        )

    display_users.short_description = "Recipients"

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
        return super(NotificationAdmin, self).changeform_view(
            request,
            object_id,
            extra_context=extra_context,
        )


admin.site.register(NotifiedUser, NotifiedUserAdmin)
admin.site.register(NotificationLog, NotificationLogAdmin)
admin.site.register(Notification, NotificationAdmin)
