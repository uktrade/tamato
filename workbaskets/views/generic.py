from django.utils.decorators import method_decorator

from common.views import CreateView
from common.views import UpdateView
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.mixins import WithCurrentWorkBasket


@method_decorator(require_current_workbasket, name="dispatch")
class DraftCreateView(WithCurrentWorkBasket, CreateView):
    """CreateView which creates or modifies drafts of a model in the current
    workbasket."""

    def get_transaction(self):
        workbasket = WorkBasket.current(self.request)
        transaction = workbasket.new_transaction()
        return transaction


@method_decorator(require_current_workbasket, name="dispatch")
class DraftUpdateView(WithCurrentWorkBasket, UpdateView):
    """UpdateView which creates or modifies drafts of a model in the current
    workbasket."""

    def get_transaction(self):
        transaction = super().get_transaction()
        transaction.workbasket = WorkBasket.current(self.request)
        return transaction
