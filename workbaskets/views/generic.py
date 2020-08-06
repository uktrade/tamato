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
    """

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.add_to_workbasket(WorkBasket.current(self.request))
        return HttpResponseRedirect(self.get_success_url())
