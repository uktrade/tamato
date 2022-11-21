from django.core.paginator import Paginator
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.base import View
from django.views.generic.edit import FormMixin

from publishing.models import PackagedWorkBasket
from workbaskets.forms import SelectableObjectsForm
from workbaskets.session_store import SessionStore

# TODO:
# * Move SelectableObjectsForm to common.forms.
# * Move SessionStore to common.session_store.


class QueuedPackagedWorkbasketView(TemplateResponseMixin, FormMixin, View):
    template_name = "publishing/queued-packaged-workbasket.jinja"
    form_class = SelectableObjectsForm

    @property
    def paginator(self):
        awaiting_queue = PackagedWorkBasket.objects.awaiting_processing()
        return Paginator(awaiting_queue, per_page=20)

    def get_initial(self):
        store = SessionStore(
            self.request,
            f"QUEUED_PACKAGED_WORKBASKET_SELECTIONS",
        )
        return store.data.copy()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        kwargs["objects"] = page.object_list
        return kwargs
