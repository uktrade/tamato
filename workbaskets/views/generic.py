from django.utils.decorators import method_decorator
from django.views import generic

from common.validators import UpdateType
from common.views import TrackedModelChangeView
from workbaskets.views.decorators import require_current_workbasket


@method_decorator(require_current_workbasket, name="dispatch")
class DraftCreateView(
    TrackedModelChangeView,
    generic.CreateView,
):
    """CreateView which creates or modifies drafts of a model in the current
    workbasket."""

    update_type = UpdateType.CREATE
    permission_required = "common.add_trackedmodel"
    success_path = "confirm-create"

    def get_transaction(self):
        return self.workbasket.new_transaction()

    def get_result_object(self, form):
        object = form.save(commit=False)
        object.update_type = self.update_type
        object.transaction = self.get_transaction()
        object.save()
        return object


@method_decorator(require_current_workbasket, name="dispatch")
class DraftUpdateView(
    TrackedModelChangeView,
    generic.UpdateView,
):
    """UpdateView which creates or modifies drafts of a model in the current
    workbasket."""

    update_type = UpdateType.UPDATE
    permission_required = "common.add_trackedmodel"
    template_name = "common/edit.jinja"
    success_path = "confirm-update"
