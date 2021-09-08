from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.urls import path
from django.urls import reverse
from django.utils.decorators import method_decorator

from exporter.tasks import upload_workbaskets
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class WorkBasketAdmin(admin.ModelAdmin):
    change_list_template = "workbasket_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        upload_url = path("upload/", self.upload, name="upload")

        return [upload_url] + urls

    @method_decorator(staff_member_required)
    def upload(self, request):
        upload_workbaskets.delay()
        self.message_user(
            request,
            f"Uploading workbaskets with status of '{WorkflowStatus.READY_FOR_EXPORT.label}'",
        )
        return HttpResponseRedirect(reverse("admin:workbaskets_workbasket_changelist"))


admin.site.register(WorkBasket, WorkBasketAdmin)
