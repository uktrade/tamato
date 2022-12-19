import logging

from django.conf import settings
from django.db.transaction import atomic
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django_fsm import TransitionNotAllowed

from common.views import WithPaginationListMixin
from publishing import forms
from publishing.models import PackagedWorkBasket
from publishing.models import PackagedWorkBasketDuplication
from publishing.models import PackagedWorkBasketInvalidCheckStatus
from publishing.models import PackagedWorkBasketInvalidQueueOperation
from publishing.models import ProcessingState
from workbaskets.models import WorkBasket


class PackagedWorkbasketQueueView(
    PermissionRequiredMixin,
    WithPaginationListMixin,
    ListView,
):
    model = PackagedWorkBasket
    permission_required = "common.add_trackedmodel"

    def get_template_names(self):
        return ["publishing/packaged_workbasket_queue.jinja"]

    def get_queryset(self):
        """Return all items that are awaiting processing or are actively being
        processed, as displayed on this view."""
        return PackagedWorkBasket.objects.filter(
            processing_state__in=ProcessingState.queued_states(),
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        data["currently_processing"] = PackagedWorkBasket.objects.currently_processing()
        return data

    def post(self, request, *args, **kwargs):
        """Manage POST requests, which can be to either pause/commence CDS
        processing or move a PackagedWorkBasket instance to the top of the
        packaging queue."""

        post = request.POST

        if post.get("promote_position"):
            url = self._promote_position(request, post.get("promote_position"))
        elif post.get("demote_position"):
            url = self._demote_position(request, post.get("demote_position"))
        elif post.get("promote_to_top_position"):
            url = self._promote_to_top_position(
                request,
                post.get("promote_to_top_position"),
            )
        elif post.get("remove_from_queue"):
            url = self._remove_from_queue(request, post.get("remove_from_queue"))
        else:
            # Handle invalid post content by redisplaying the page.
            url = request.build_absolute_uri()

        return HttpResponseRedirect(url)

    # Queue item position management.

    def _promote_position(self, request, pk):
        try:
            packaged_work_basket = PackagedWorkBasket.objects.get(pk=pk)
            packaged_work_basket.promote_position()
        except (
            PackagedWorkBasket.DoesNotExist,
            PackagedWorkBasketInvalidQueueOperation,
        ):
            # Nothing to do in the case of these exceptions.
            pass
        return request.build_absolute_uri()

    def _demote_position(self, request, pk):
        try:
            packaged_work_basket = PackagedWorkBasket.objects.get(pk=pk)
            packaged_work_basket.demote_position()
        except (
            PackagedWorkBasket.DoesNotExist,
            PackagedWorkBasketInvalidQueueOperation,
        ):
            # Nothing to do in the case of these exceptions.
            pass
        return request.build_absolute_uri()

    def _promote_to_top_position(self, request, pk):
        try:
            packaged_work_basket = PackagedWorkBasket.objects.get(pk=pk)
            packaged_work_basket.promote_to_top_position()
        except (
            PackagedWorkBasket.DoesNotExist,
            PackagedWorkBasketInvalidQueueOperation,
        ):
            # Nothing to do in the case of these exceptions.
            pass
        return request.build_absolute_uri()

    def _remove_from_queue(self, request, pk):
        try:
            packaged_work_basket = PackagedWorkBasket.objects.get(pk=pk)
            packaged_work_basket.abandon()
            return reverse(
                "workbaskets:workbasket-ui-changes",
                kwargs={"pk": packaged_work_basket.workbasket.pk},
            )
        except (
            PackagedWorkBasket.DoesNotExist,
            PackagedWorkBasketInvalidQueueOperation,
            TransitionNotAllowed,
        ):
            # Nothing to do in the case of these exceptions.
            return request.build_absolute_uri()


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
        return PackagedWorkBasket.objects.all_queued()

    def post(self, request, *args, **kwargs):
        """Manage POST requests, including download, accept and reject
        envelopes."""
        # TODO: manage post actions.
        return super().post()


class PackagedWorkbasketCreateView(PermissionRequiredMixin, CreateView):
    """UI endpoint for creating packaged workbaskets."""

    permission_required = "publishing.add_packagedworkbasket"
    template_name = "publishing/create.jinja"
    form_class = forms.PackagedWorkBasketCreateForm

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)

    @property
    def workbasket(self):
        """Current Workbasket in session."""
        return WorkBasket.current(self.request)

    @atomic
    def form_valid(self, form):
        """If form is valid submit workbasket state from EDITING -> PROPOSED ->
        APPROVED, then create the packaged workbasket in the queue and then go
        to create confirmation."""
        wb = self.workbasket
        try:
            wb.submit_for_approval()
            wb.save()
        except ValidationError as err:
            self.logger.error(
                "Error: %s \n Redirecting to work basket %s summary",
                err.message,
                self.workbasket.id,
            )
            return redirect(
                "workbaskets:workbasket-ui-detail",
                pk=self.workbasket.id
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
                err,
            )
            return redirect(
                "publishing:packaged-workbasket-queue-ui-list"
            )
        except PackagedWorkBasketInvalidCheckStatus as err:
            self.logger.error(
                "Error: %s \n Redirecting to packaged work basket %s summary",
                err,
                self.workbasket.id,
            )
            return redirect(
                "workbaskets:workbasket-ui-detail",
                pk=self.workbasket.id
            )

        return redirect(
            "publishing:packaged-workbasket-queue-confirm-create",
            pk=queued_wb.pk
        )

class PackagedWorkbasketConfirmCreate(DetailView):
    template_name = "publishing/confirm_create.jinja"
    model = PackagedWorkBasket

    def get_queryset(self):
        """Return package work basket based on packaged workbasket pk."""
        return PackagedWorkBasket.objects.filter(
            id=self.kwargs.get("pk"),
        )
