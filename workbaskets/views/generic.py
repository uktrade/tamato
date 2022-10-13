from django.utils.decorators import method_decorator
from django.views import generic

from common.validators import UpdateType
from common.views import TrackedModelChangeView
from workbaskets.views.decorators import require_current_workbasket


@method_decorator(require_current_workbasket, name="dispatch")
class CreateTaricCreateView(
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
class CreateTaricUpdateView(
    TrackedModelChangeView,
    generic.UpdateView,
):
    """UpdateView which creates or modifies drafts of a model in the current
    workbasket."""

    update_type = UpdateType.UPDATE
    permission_required = "common.add_trackedmodel"
    template_name = "common/edit.jinja"
    success_path = "confirm-update"


@method_decorator(require_current_workbasket, name="dispatch")
class CreateTaricDeleteView(
    TrackedModelChangeView,
    generic.UpdateView,
):
    """Creates a new TrackedModel instance which is marked as deleted."""

    update_type = UpdateType.DELETE
    permission_required = "common.add_trackedmodel"
    template_name = "common/delete.jinja"


@method_decorator(require_current_workbasket, name="dispatch")
class EditTaricCreateView(
    TrackedModelChangeView,
    generic.UpdateView,
):
    """
    View used to change an existing model instance in the current workbasket
    without creating a new version. The model instance may have an update_type.

    of either Create or Update - Delete is not an editable update type.
    """

    permission_required = "common.add_trackedmodel"
    success_path = "confirm-update"

    def get_template_names(self):
        return "common/edit.jinja"

    def get_result_object(self, form):
        """Override the default behaviour in order to only update the existing
        instance of the TrackedModel (i.e. without changing the object's
        version)."""
        return form.save()
