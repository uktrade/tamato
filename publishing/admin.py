from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from publishing.models import OperationalStatus
from publishing.models import PackagedWorkBasket


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
        "pk",
        "position",
        "processing_state",
        "workbasket",
    )
    list_filter = (
        CustomProcessingStateFilter,
        "processing_state",
    )
    ordering = ["position"]


admin.site.register(PackagedWorkBasket, PackagedWorkBasketAdmin)


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
