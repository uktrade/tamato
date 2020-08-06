from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView

from common.validators import UpdateType
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.mixins import WithCurrentWorkBasket


@method_decorator(require_current_workbasket, name="dispatch")
class DraftUpdateView(WithCurrentWorkBasket, UpdateView):
    """
    UpdateView which creates or modifies drafts of a model in the current workbasket.

    Set `update_fields` to a list of field names to update on form submission.
    """

    def form_valid(self, form):
        workbasket = WorkBasket.current(self.request)

        # if there is already a draft in the workbasket, update it
        if self.object.workbasket == workbasket:
            self.object.update_type = UpdateType.UPDATE
            for field_name in self.update_fields:
                setattr(self.object, field_name, form.cleaned_data.get(field_name))
            self.object.save(update_fields=self.update_fields)

        # otherwise, create a new draft
        else:
            self.object = self.object.new_draft(
                workbasket=workbasket,
                update_type=UpdateType.UPDATE,
                **{
                    field_name: form.cleaned_data.get(field_name)
                    for field_name in self.update_fields
                },
            )

        return HttpResponseRedirect(self.get_success_url())
