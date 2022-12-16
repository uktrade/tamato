import logging
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView

from common.views import WithPaginationListMixin
from publishing import forms
from publishing.models import PackagedWorkBasket
from publishing.models import PackagedWorkBasketDuplication
from publishing.models import PackagedWorkBasketInvalidCheckStatus
from publishing.models import ProcessingState
from workbaskets.models import WorkBasket



class PackagedWorkbasketQueueView(
    PermissionRequiredMixin,
    WithPaginationListMixin,
    ListView,
):
    model = PackagedWorkBasket
    permission_required = ""  # TODO: select permissions.

    def get_template_names(self):
        return ["publishing/packaged_workbasket_queue.jinja"]

    def get_queryset(self):
        """Return all items that are awaiting processing or are actively being
        processed, as displayed on this view."""
        return PackagedWorkBasket.objects.filter(
            processing_state__in=(
                ProcessingState.queued_states()
                + (ProcessingState.CURRENTLY_PROCESSING,)
            ),
        )

    def post(self, request, *args, **kwargs):
        """Manage POST requests, which can be to either pause/commence CDS
        processing or move a PackagedWorkBasket instance to the top of the
        packaging queue."""
        # TODO: manage post actions.
        return super().post()


class EnvelopeQueueView(
    PermissionRequiredMixin,
    WithPaginationListMixin,
    ListView,
):
    model = PackagedWorkBasket
    permission_required = ""  # TODO: select permissions.

    def get_template_names(self):
        return ["publishing/envelope_queue.jinja"]

    def get_queryset(self):
        """Return all items that are awaiting processing or are actively being
        processed, as displayed on this view."""
        return PackagedWorkBasket.objects.filter(
            processing_state__in=(
                ProcessingState.active_states() + ProcessingState.queued_states()
            ),
        )

    def post(self, request, *args, **kwargs):
        """Manage POST requests, including download, accept and reject
        envelopes."""
        # TODO: manage post actions.
        return super().post()


class PackagedWorkbasketCreateView(PermissionRequiredMixin, CreateView):
    """UI endpoint for creating packaged workbaskets."""

    permission_required = "workbaskets.add_workbasket"
    template_name = "publishing/create.jinja"
    form_class = forms.PackagedWorkBasketCreateForm

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)

    @property
    def workbasket(self):
        return WorkBasket.current(self.request)

    def form_valid(self, form):
        wb = self.workbasket
        try:
            wb.submit_for_approval()
            wb.save()
        except ValidationError as err:
            self.logger.error(
                "Error: %s \n Redirecting to work basket %s summary",
                err.message,
                self.workbasket.id
                )
            return redirect(
                reverse(
                    "workbaskets:workbasket-ui-detail",
                    kwargs={"pk": self.workbasket.id},
                ),
            )

        wb.approve(self.request.user, settings.TRANSACTION_SCHEMA)
        wb.save()

        queued_wb = None
        try:
            queued_wb = PackagedWorkBasket.objects.create(
                workbasket=wb, **form.cleaned_data
            )
        except PackagedWorkBasketDuplication as err:
            self.logger.error(
                "Error: %s \n Redirecting to packaged work basket queue",
                err
                )
            return redirect(
                reverse(
                    "publishing:packaged-workbasket-queue-ui-list",
                ),
            )
        except PackagedWorkBasketInvalidCheckStatus as err:
            self.logger.error(
                "Error: %s \n Redirecting to packaged work basket %s summary",
                err,
                self.workbasket.id
                )
            return redirect(
                reverse(
                    "workbaskets:workbasket-ui-detail",
                    kwargs={"pk": self.workbasket.id},
                ),
            )

        return redirect(
            reverse(
                "publishing:packaged-workbasket-queue-confirm-create",
                kwargs={"pk": queued_wb.pk},
            ),
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class PackagedWorkbasketConfirmCreate(DetailView):
    template_name = "publishing/confirm_create.jinja"
    model = PackagedWorkBasket

    def get_queryset(self):
        """Return all items that are awaiting processing or are actively being
        processed, as displayed on this view."""
        return PackagedWorkBasket.objects.filter(
            id=self.kwargs.get("pk"),
        )
