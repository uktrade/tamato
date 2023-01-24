from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from publishing.models.envelope import Envelope
from publishing.models.operational_status import OperationalStatus
from publishing.models.packaged_workbasket import PackagedWorkBasket


class CustomProcessingStateFilter(admin.SimpleListFilter):
    title = "Custom processing state"
    parameter_name = "custom_processing_state"

    def lookups(self, request, model_admin):
        return (
            (None, "Only queued"),
            ("all", _("All")),
        )

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == str(lookup),
                "query_string": changelist.get_query_string(
                    {self.parameter_name: lookup},
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        if self.value() == None:
            return queryset.all_queued()


class PackagedWorkBasketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "position",
        "processing_state",
        "workbasket_id",
        "workbasket_title",
    )
    list_filter = (
        CustomProcessingStateFilter,
        "processing_state",
    )
    ordering = ["position"]

    def workbasket_id(self, obj):
        if not obj.workbasket:
            return "Missing workbasket!"
        return obj.workbasket.id

    def workbasket_title(self, obj):
        if not obj.workbasket:
            return "Missing workbasket!"
        return obj.workbasket.title


admin.site.register(PackagedWorkBasket, PackagedWorkBasketAdmin)


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
