from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView
from django.views.generic import TemplateView

from common.validators import UpdateType
from common.views.mixins import TrackedModelDetailMixin
from measures import forms
from workbaskets.models import WorkBasket
from workbaskets.views.generic import CreateTaricDeleteView

from .mixins import MeasureMixin
from .mixins import MeasureSelectionQuerysetMixin


class MeasureDelete(
    MeasureMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.MeasureDeleteForm
    success_path = "list"


class MeasureMultipleDelete(MeasureSelectionQuerysetMixin, TemplateView, ListView):
    """UI for user review and deletion of multiple Measures."""

    template_name = "measures/delete-multiple-measures.jinja"

    def get_context_data(self, **kwargs):
        store_objects = self.get_queryset()
        self.object_list = store_objects
        context = super().get_context_data(**kwargs)

        return context

    def post(self, request):
        if request.POST.get("action", None) != "delete":
            # The user has cancelled out of the deletion process.
            return redirect("home")

        workbasket = WorkBasket.current(request)
        object_list = self.get_queryset()

        for obj in object_list:
            # make a new version of the object with an update type of delete.
            obj.new_version(
                workbasket=workbasket,
                update_type=UpdateType.DELETE,
            )
        self.session_store.clear()

        return redirect(
            reverse(
                "workbaskets:workbasket-ui-review-measures",
                kwargs={"pk": workbasket.pk},
            ),
        )
