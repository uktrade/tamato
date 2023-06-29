from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from importer.models import ImportBatch
from publishing.admin import WorkBasketAdminMixin


class ImportBatchAdmin(
    WorkBasketAdminMixin,
    admin.ModelAdmin,
):
    ordering = ["-pk"]
    list_display = (
        "id",
        "name",
        "author",
        "status",
        "split_job",
        "workbasket_id",
        "workbasket_title",
        "download_taric_envelope",
    )

    def workbasket_id(self, obj):
        if not obj.workbasket:
            return "No associated workbasket."
        return self.workbasket_id_link(obj.workbasket)

    def workbasket_title(self, obj):
        if not obj.workbasket:
            return "No associated workbasket."
        return obj.workbasket.title

    def download_taric_envelope(self, obj):
        if not obj.taric_file:
            return None

        download_url = reverse(
            "admin-taric-ui-download",
            args=(obj.pk,),
        )
        return mark_safe(
            f'<a href="{download_url}">{obj.name}</a>',
        )


admin.site.register(ImportBatch, ImportBatchAdmin)
