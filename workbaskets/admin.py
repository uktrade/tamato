from django import forms
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.urls import path
from django.urls import reverse
from django.utils.decorators import method_decorator

from exporter.tasks import upload_workbaskets
from workbaskets.models import WorkBasket
from workbaskets.models import get_partition_scheme
from workbaskets.validators import WorkflowStatus


class WorkBasketAdminForm(forms.ModelForm):
    class Meta:
        model = WorkBasket
        fields = ["title", "reason", "transition"]

    transition = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields["transition"].choices = [
                ("", "--- Keep current status ---"),
            ] + [
                (transition.name, transition.custom["label"])
                for transition in self.instance.get_available_status_transitions()
            ]

            if len(self.fields["transition"].choices) == 1:
                self.fields["transition"].disabled = True

        else:
            del self.fields["transition"]


class WorkBasketAdmin(admin.ModelAdmin):
    form = WorkBasketAdminForm
    actions = ["approve", "publish"]
    change_list_template = "workbasket_change_list.html"
    list_display = (
        "pk",
        "title",
        "author",
        "status",
        "approver",
        "created_at",
        "updated_at",
    )
    list_filter = (
        ("author", admin.RelatedOnlyFieldListFilter),
        "status",
        ("approver", admin.RelatedOnlyFieldListFilter),
    )
    ordering = ["-updated_at"]
    search_fields = (
        "pk",
        "title",
        "reason",
    )

    def get_urls(self):
        urls = super().get_urls()
        upload_url = path("upload/", self.upload, name="upload")

        return [upload_url] + urls

    @method_decorator(staff_member_required)
    def upload(self, request):
        upload_workbaskets.delay()
        self.message_user(
            request,
            f"Uploading workbaskets with status of '{WorkflowStatus.APPROVED.label}'",
        )
        return HttpResponseRedirect(reverse("admin:workbaskets_workbasket_changelist"))

    def save_model(self, request, instance, form, change):
        instance = form.save(commit=False)
        if not change or not instance.author:
            instance.author = request.user

        transition = form.cleaned_data.get("transition")
        if transition:
            transition_args = []
            if transition == "approve":
                transition_args.extend([request.user, get_partition_scheme()])
            getattr(instance, transition)(*transition_args)

        instance.save()
        form.save_m2m()
        return instance


admin.site.register(WorkBasket, WorkBasketAdmin)
