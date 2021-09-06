from django.contrib import admin
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseForbidden
from django.urls import path

from exporter.tasks import upload_workbaskets
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

class WorkBasketAdmin(admin.ModelAdmin):
    change_list_template = "workbasket_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        export_url = path('upload/', self.upload)
        
        return [export_url] + urls
    
    def upload(self, request):
        if not request.user.is_superuser:
            return HttpResponseForbidden('Only superusers may export workbaskets')
        
        upload_workbaskets.delay()
        self.message_user(request, f"Uploading workbaskets with status of '{WorkflowStatus.READY_FOR_EXPORT.label}'")
        return HttpResponseRedirect("../")


admin.site.register(WorkBasket, WorkBasketAdmin)