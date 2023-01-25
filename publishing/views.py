import logging

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django_fsm import TransitionNotAllowed

from common.views import WithPaginationListMixin
from publishing.forms import LoadingReportForm
from publishing.forms import PackagedWorkBasketCreateForm
from publishing.models.exceptions import PackagedWorkBasketDuplication
from publishing.models.exceptions import PackagedWorkBasketInvalidCheckStatus
from publishing.models.exceptions import PackagedWorkBasketInvalidQueueOperation
from publishing.models.operational_status import OperationalStatus
from publishing.models.packaged_workbasket import PackagedWorkBasket
from publishing.models.state import ProcessingState
from workbaskets.models import WorkBasket


class PackagedWorkbasketQueueView(
    PermissionRequiredMixin,
    WithPaginationListMixin,
    ListView,
):
    """UI view used to manage (ordering, pausing, removal) packaged
    workbaskets."""

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
        data["queue_paused"] = OperationalStatus.is_queue_paused()
        return data

    def post(self, request, *args, **kwargs):
        """Manage POST requests, which can be to either pause/commence CDS
        processing or move a PackagedWorkBasket instance to the top of the
        packaging queue."""

        post = request.POST

        if post.get("pause_queue"):
            url = self._pause_queue(request)
        elif post.get("unpause_queue"):
            url = self._unpause_queue(request)
        elif post.get("promote_position"):
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

        return redirect(url)

    # Queue item position management.

    def _pause_queue(self, request):
        OperationalStatus.pause_queue(user=request.user)
        return request.build_absolute_uri()

    def _unpause_queue(self, request):
        OperationalStatus.unpause_queue(user=request.user)
        return request.build_absolute_uri()

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
    """UI view used to download and manage envelope processing."""

    model = PackagedWorkBasket
    permission_required = "common.add_trackedmodel"

    def get_template_names(self):
        return ["publishing/envelope_queue.jinja"]

    def get_queryset(self):
        """Return all items that are awaiting processing or are actively being
        processed, as displayed on this view."""
        return PackagedWorkBasket.objects.all_queued()

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        data["currently_processing"] = PackagedWorkBasket.objects.currently_processing()
        data["queue_paused"] = OperationalStatus.is_queue_paused()
        return data

    def post(self, request, *args, **kwargs):
        """Manage POST requests, including download, accept and reject
        envelopes."""

        post = request.POST

        if post.get("process_envelope"):
            url = self._process_envelope(request, post.get("process_envelope"))
        else:
            # Handle invalid post content by redisplaying the page.
            url = request.build_absolute_uri()

        return redirect(url)

    def _process_envelope(self, request, pk):
        if not OperationalStatus.is_queue_paused():
            packaged_work_basket = PackagedWorkBasket.objects.get(pk=pk)
            try:
                packaged_work_basket.begin_processing()
            except TransitionNotAllowed:
                # No error page right now, just reshow the list view.
                pass
        return request.build_absolute_uri()


class DownloadQueuedEnvelopeView(PermissionRequiredMixin, DetailView):
    """View used to download an XML envelope."""

    permission_required = "common.add_trackedmodel"
    model = PackagedWorkBasket

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponse

        packaged_workbasket = self.get_object()

        envelope = packaged_workbasket.envelope
        file_content = envelope.xml_file.read()
        file_name = f"DIT{envelope.envelope_id}.xml"

        response = HttpResponse(file_content)
        response["content-type"] = "text/xml"
        response["content-length"] = len(file_content)
        response["content-disposition"] = f'attachment; filename="{file_name}"'

        return response


class CompleteEnvelopeProcessingView(PermissionRequiredMixin, CreateView):
    """Generic UI view used to confirm envelope processing."""

    permission_required = "workbaskets.change_workbasket"
    template_name = "publishing/complete-envelope-processing.jinja"
    form_class = LoadingReportForm

    @atomic
    def form_valid(self, form):
        """Create a LoadingReport instance, associated it wth the
        PackagedWorkBasket and transition that PackagedWorkBasket instance to
        the next, completed processing state (either succeeded or failed)."""

        packaged_work_basket = PackagedWorkBasket.objects.get(
            pk=self.kwargs["pk"],
        )
        self.object = form.save()
        packaged_work_basket.loading_report = self.object
        packaged_work_basket.save()
        self.transition_packaged_work_basket(packaged_work_basket)

        return redirect(self.get_success_url())

    def transition_packaged_work_basket(self, packaged_work_basket):
        raise NotImplementedError()


class EnvelopeActionConfirmView(DetailView):
    template_name = "publishing/complete-envelope-processing-confirm.jinja"
    model = PackagedWorkBasket


class AcceptEnvelopeView(CompleteEnvelopeProcessingView):
    """UI view used to accept an envelope as having been processed by HMRC
    systems (CDS, etc)."""

    def get_success_url(self):
        return reverse(
            "publishing:accept-envelope-confirm-ui-detail",
            kwargs={"pk": self.kwargs["pk"]},
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        data["accept_reject"] = "accept"
        return data

    def transition_packaged_work_basket(self, packaged_work_basket):
        return packaged_work_basket.processing_succeeded()


class AcceptEnvelopeConfirmView(EnvelopeActionConfirmView):
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        packaged_workbasket = self.get_object()
        envelope = packaged_workbasket.envelope

        data["message"] = f"Envelope ID {envelope.envelope_id} was accepted."
        return data


class RejectEnvelopeView(CompleteEnvelopeProcessingView):
    """UI view used to reject an envelope as having failed to be processed by
    HMRC systems (CDS, etc)."""

    def get_success_url(self):
        return reverse(
            "publishing:reject-envelope-confirm-ui-detail",
            kwargs={"pk": self.kwargs["pk"]},
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        data["accept_reject"] = "reject"
        return data

    def transition_packaged_work_basket(self, packaged_work_basket):
        OperationalStatus.pause_queue(user=None)
        return packaged_work_basket.processing_failed()


class RejectEnvelopeConfirmView(EnvelopeActionConfirmView):
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        packaged_workbasket = self.get_object()
        envelope = packaged_workbasket.envelope

        data[
            "message"
        ] = f"Envelope ID {envelope.envelope_id} was rejected and queue was paused."
        return data


class PackagedWorkbasketCreateView(PermissionRequiredMixin, CreateView):
    """UI endpoint for creating packaged workbaskets."""

    permission_required = "publishing.add_packagedworkbasket"
    template_name = "publishing/create.jinja"
    form_class = PackagedWorkBasketCreateForm

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
            wb.queue(self.request.user, settings.TRANSACTION_SCHEMA)
            wb.save()
        except ValidationError as err:
            self.logger.error(
                "Error: %s \n Redirecting to work basket %s summary",
                err.message,
                self.workbasket.id,
            )
            return redirect(
                "workbaskets:workbasket-ui-detail",
                pk=self.workbasket.id,
            )

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
                "publishing:packaged-workbasket-queue-ui-list",
            )
        except PackagedWorkBasketInvalidCheckStatus as err:
            self.logger.error(
                "Error: %s \n Redirecting to packaged work basket %s summary",
                err,
                self.workbasket.id,
            )
            return redirect(
                "workbaskets:workbasket-ui-detail",
                pk=self.workbasket.id,
            )

        return redirect(
            "publishing:packaged-workbasket-queue-confirm-create",
            pk=queued_wb.pk,
        )


class PackagedWorkbasketConfirmCreate(DetailView):
    template_name = "publishing/confirm_create.jinja"
    model = PackagedWorkBasket

    def get_queryset(self):
        """Return package work basket based on packaged workbasket pk."""
        return PackagedWorkBasket.objects.filter(
            id=self.kwargs.get("pk"),
        )
