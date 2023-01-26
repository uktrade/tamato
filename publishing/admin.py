from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from publishing.models import Envelope
from publishing.models import OperationalStatus
from publishing.models import PackagedWorkBasket
from publishing.models import ProcessingState


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


class EnvelopeDeletedFilter(admin.SimpleListFilter):
    title = "Deleted state"
    parameter_name = "deleted_state"

    def lookups(self, request, model_admin):
        return (
            ("DELETED", _("Deleted")),
            ("NOT_DELETED", _("Not deleted")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "DELETED":
            return queryset.deleted()
        elif value == "NOT_DELETED":
            return queryset.non_deleted()


class CustomEnvelopeProcessingStateFilter(admin.SimpleListFilter):
    title = "Processing state"
    parameter_name = "processing_state"

    def lookups(self, request, model_admin):
        return (
            ("UNPROCESSED", _("Unprocessed")),
            (ProcessingState.CURRENTLY_PROCESSING, _("Currently processing")),
            (ProcessingState.SUCCESSFULLY_PROCESSED, _("Successfully processed")),
            (ProcessingState.FAILED_PROCESSING, _("Failed processing")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "UNPROCESSED":
            return queryset.unprocessed()
        elif value == ProcessingState.CURRENTLY_PROCESSING:
            return queryset.currently_processing()
        elif value == ProcessingState.SUCCESSFULLY_PROCESSED:
            return queryset.successfully_processed()
        elif value == ProcessingState.FAILED_PROCESSING:
            return queryset.failed_processing()


class EnvelopeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "envelope_id",
        "packagedworkbaskets_processing_state",
        "packagedworkbaskets_workbasket_id",
        "deleted",
        # TODO add user
    )
    ordering = ["-pk"]

    list_filter = (
        EnvelopeDeletedFilter,
        CustomEnvelopeProcessingStateFilter,
    )

    def packagedworkbaskets_processing_state(self, obj):
        return obj.packagedworkbaskets.get().processing_state

    def packagedworkbaskets_workbasket_id(self, obj):
        return obj.packagedworkbaskets.get().workbasket_id


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
