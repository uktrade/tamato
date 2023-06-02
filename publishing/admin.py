from django import forms
from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe

from publishing.models import CrownDependenciesEnvelope
from publishing.models import CrownDependenciesPublishingOperationalStatus
from publishing.models import CrownDependenciesPublishingTask
from publishing.models import Envelope
from publishing.models import LoadingReport
from publishing.models import OperationalStatus
from publishing.models import PackagedWorkBasket
from publishing.models import ProcessingState
from publishing.models.state import CrownDependenciesPublishingState
from workbaskets.models import WorkBasket


class WorkBasketAdminMixin:
    """Provides admin utility methods."""

    def workbasket_id_link(self, workbasket: WorkBasket):
        """Returns a HRML anchor element linked to `workbasket`'s admin change
        view."""
        workbasket_url = reverse(
            "admin:workbaskets_workbasket_change",
            args=(workbasket.pk,),
        )
        return mark_safe(
            f'<a href="{workbasket_url}">{workbasket.pk}</a>',
        )


class PackagedWorkBasketAdminMixin:
    """Provide utility methods."""

    def packaged_workbasket_id_link(self, packaged_workbasket: PackagedWorkBasket):
        """Returns a HRML anchor element linked to `packaged_workbasket`'s admin
        change view."""
        pwb_url = reverse(
            "admin:publishing_packagedworkbasket_change",
            args=(packaged_workbasket.pk,),
        )
        return mark_safe(f'<a href="{pwb_url}">{packaged_workbasket.pk}</a>')


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


class PackagedWorkBasketAdmin(WorkBasketAdminMixin, admin.ModelAdmin):
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
        return self.workbasket_id_link(obj.workbasket)

    def workbasket_title(self, obj):
        if not obj.workbasket:
            return "Missing workbasket!"
        return obj.workbasket.title


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


class EnvelopeAdmin(
    PackagedWorkBasketAdminMixin,
    WorkBasketAdminMixin,
    admin.ModelAdmin,
):
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
        return self.packaged_workbasket_id_link(pwb)

    def workbasket_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return None

        if not pwb.workbasket:
            return None

        return self.workbasket_id_link(pwb.workbasket)

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


class LoadingReportAdmin(
    PackagedWorkBasketAdminMixin,
    WorkBasketAdminMixin,
    admin.ModelAdmin,
):
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
        return self.packaged_workbasket_id_link(pwb)

    def workbasket_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return "Missing packaged workbasket!"

        if not pwb.workbasket:
            return "Missing workbasket!"

        return self.workbasket_id_link(pwb.workbasket)


class CrownDependenciesEnvelopeAdmin(
    PackagedWorkBasketAdminMixin,
    WorkBasketAdminMixin,
    admin.ModelAdmin,
):
    ordering = ["-pk"]
    list_display = (
        "id",
        "envelope_id",
        "publishing_state",
        "published",
        "packaged_workbasket_id",
        "workbasket_id",
    )
    list_filter = ("publishing_state",)

    def envelope_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return "Missing packaged workbasket!"
        return pwb.envelope.envelope_id

    def packaged_workbasket_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return "Missing packaged workbasket!"
        return self.packaged_workbasket_id_link(pwb)

    def workbasket_id(self, obj):
        pwb = obj.packagedworkbaskets.last()
        if not pwb:
            return "Missing packaged workbasket!"

        if not pwb.workbasket:
            return "Missing workbasket!"

        return self.workbasket_id_link(pwb.workbasket)


class CrownDependenciesPublishingTaskAdminForm(forms.ModelForm):
    class Meta:
        model = CrownDependenciesPublishingTask
        fields = [
            "terminate_task",
        ]
        readonly_fields = (
            "task_id",
            "task_status",
        )

    task_status = forms.CharField(required=False)
    terminate_task = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields["task_id"].disabled = True
            self.fields["task_status"].disabled = True
            self.fields["task_status"].initial = self.instance.task_status


class CrownDependenciesPublishingTaskAdmin(admin.ModelAdmin):
    ordering = ["-pk"]
    list_display = (
        "id",
        "task_status",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            None,
            {
                "fields": ("task_id", "task_status", "terminate_task"),
            },
        ),
    )
    form = CrownDependenciesPublishingTaskAdminForm

    def task_status(self, obj):
        task_status = obj.task_status
        if not task_status:
            return "UNAVAILABLE"
        return task_status

    def save_model(self, request, instance, form, change):
        super().save_model(request, instance, form, change)

        terminate_task = form.cleaned_data.get("terminate_task")
        if terminate_task:
            instance.terminate_task()

        return instance

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CrownDependenciesPublishingOperationalStatusAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "publishing_state",
        "created_by",
        "created_at",
    )
    ordering = ["-pk"]

    def save_model(self, request, obj, form, change):
        state = form.cleaned_data.get("publishing_state")
        if state == CrownDependenciesPublishingState.PAUSED:
            new_status = CrownDependenciesPublishingOperationalStatus.pause_publishing(
                user=request.user,
            )
        else:
            new_status = (
                CrownDependenciesPublishingOperationalStatus.unpause_publishing(
                    user=request.user,
                )
            )

        if not new_status:
            messages.set_level(request, messages.ERROR)
            messages.error(
                request,
                f"Operational status of publishing is already in state: {state}",
            )
            return

        new_status.save()
        messages.set_level(request, messages.SUCCESS)
        messages.success(
            request,
            f"Operational status of publishing is now in state: {state}",
        )
        return

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Envelope, EnvelopeAdmin)

admin.site.register(LoadingReport, LoadingReportAdmin)

admin.site.register(OperationalStatus, OperationalStatusAdmin)

admin.site.register(PackagedWorkBasket, PackagedWorkBasketAdmin)

admin.site.register(CrownDependenciesEnvelope, CrownDependenciesEnvelopeAdmin)

admin.site.register(
    CrownDependenciesPublishingTask,
    CrownDependenciesPublishingTaskAdmin,
)

admin.site.register(
    CrownDependenciesPublishingOperationalStatus,
    CrownDependenciesPublishingOperationalStatusAdmin,
)
