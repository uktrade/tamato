from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from publishing.models import Envelope
from publishing.models import LoadingReport
from publishing.models import OperationalStatus
from publishing.models import PackagedWorkBasket
from publishing.models import ProcessingState


class PackagedWorkBasketProcessingStateFilter(admin.SimpleListFilter):
    title = "Custom processing state"
    parameter_name = "custom_processing_state"

    def lookups(self, request, model_admin):
        return (
            (None, "Only queued"),
            ("all", "All"),
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
    ordering = ["position"]
    list_display = (
        "id",
        "position",
        "processing_state",
        "workbasket_id",
        "workbasket_title",
    )
    list_filter = (
        PackagedWorkBasketProcessingStateFilter,
        "processing_state",
    )

    def workbasket_id(self, obj):
        if not obj.workbasket:
            return "Missing workbasket!"

        workbasket_url = reverse(
            "admin:workbaskets_workbasket_change",
            args=(obj.workbasket.pk,),
        )
        return mark_safe(
            f'<a href="{workbasket_url}">{obj.workbasket.pk}</a>',
        )

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
            ("DELETED", "Deleted"),
            ("NOT_DELETED", "Not deleted"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "DELETED":
            return queryset.deleted()
        elif value == "NOT_DELETED":
            return queryset.non_deleted()


class EnvelopeProcessingStateFilter(admin.SimpleListFilter):
    title = "Processing state"
    parameter_name = "processing_state"

    def lookups(self, request, model_admin):
        return (
            ("UNPROCESSED", "Unprocessed"),
            (ProcessingState.CURRENTLY_PROCESSING, "Currently processing"),
            (ProcessingState.SUCCESSFULLY_PROCESSED, "Successfully processed"),
            (ProcessingState.FAILED_PROCESSING, "Failed processing"),
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
    ordering = ["-pk"]
    list_display = (
        "id",
        "envelope_id",
        "processing_state",
        "packaged_workbasket_id",
        "workbasket_id",
        "download_envelope",
        "published_to_tariffs_api",
        "deleted",
    )
    list_filter = (
        EnvelopeDeletedFilter,
        EnvelopeProcessingStateFilter,
        "published_to_tariffs_api",
    )

    def processing_state(self, obj):
        return obj.packagedworkbaskets.get().get_processing_state_display()

    def packaged_workbasket_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return None

        pwb_url = reverse(
            "admin:publishing_packagedworkbasket_change",
            args=(pwb.pk,),
        )
        return mark_safe(f'<a href="{pwb_url}">{pwb.pk}</a>')

    def workbasket_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return None

        if not pwb.workbasket:
            return None

        workbasket_url = reverse(
            "admin:workbaskets_workbasket_change",
            args=(pwb.workbasket.pk,),
        )
        return mark_safe(
            f'<a href="{workbasket_url}">{pwb.workbasket.pk}</a>',
        )

    def download_envelope(self, obj):
        if (
            obj.packagedworkbaskets.get().processing_state
            in ProcessingState.completed_processing_states()
            and not obj.xml_file
        ):
            return "Missing envelope!"
        elif not obj.xml_file:
            return None

        download_url = reverse(
            "publishing:admin-envelope-ui-download",
            args=(obj.packagedworkbaskets.get().pk,),
        )
        return mark_safe(
            f'<a href="{download_url}">{obj.envelope_id}</a>',
        )


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


class LoadingReportAcceptedRejectedFilter(admin.SimpleListFilter):
    title = "Accepted or rejected"
    parameter_name = "accepted_rejected"

    def lookups(self, request, model_admin):
        return (
            ("ACCEPTED", "Accepted"),
            ("REJECTED", "Rejected"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "ACCEPTED":
            return queryset.accepted()
        elif value == "REJECTED":
            return queryset.rejected()


class LoadingReportAdmin(admin.ModelAdmin):
    ordering = ["-pk"]
    list_display = (
        "id",
        "file_download",
        "comments",
        "accepted_or_rejected",
        "packaged_workbasket_id",
        "workbasket_id",
    )
    list_filter = (LoadingReportAcceptedRejectedFilter,)

    def file_download(self, obj):
        if not obj.file:
            return None

        file_name = obj.file_name if obj.file_name else "UNKNOWN_FILENAME"

        download_url = reverse(
            "publishing:admin-loading-report-ui-download",
            args=(obj.pk,),
        )
        return mark_safe(
            f'<a href="{download_url}">{file_name}</a>',
        )

    def accepted_or_rejected(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return "Missing packaged workbasket!"

        state = pwb.processing_state
        if state == ProcessingState.SUCCESSFULLY_PROCESSED:
            return "Accepted"
        elif state == ProcessingState.FAILED_PROCESSING:
            return "Rejected"

        return f"Unexpected state"

    def packaged_workbasket_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return "Missing packaged workbasket!"

        pwb_url = reverse(
            "admin:publishing_packagedworkbasket_change",
            args=(pwb.pk,),
        )
        return mark_safe(f'<a href="{pwb_url}">{pwb.pk}</a>')

    def workbasket_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return "Missing packaged workbasket!"

        if not pwb.workbasket:
            return "Missing workbasket!"

        workbasket_url = reverse(
            "admin:workbaskets_workbasket_change",
            args=(pwb.workbasket.pk,),
        )
        return mark_safe(
            f'<a href="{workbasket_url}">{pwb.workbasket.pk}</a>',
        )


admin.site.register(OperationalStatus, OperationalStatusAdmin)

admin.site.register(Envelope, EnvelopeAdmin)

admin.site.register(LoadingReport, LoadingReportAdmin)
