import logging

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic.detail import BaseDetailView
from django_fsm import TransitionNotAllowed

from common.filters import TamatoFilter
from common.util import get_mime_type
from common.views import WithPaginationListMixin
from common.views import WithPaginationListView
from publishing.forms import LoadingReportForm
from publishing.forms import PackagedWorkBasketCreateForm
from publishing.models import Envelope
from publishing.models import LoadingReport
from publishing.models import OperationalStatus
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
    """UI view used to manage (ordering, pausing, removal) packaged
    workbaskets."""

    model = PackagedWorkBasket
    permission_required = "publishing.manage_packaging_queue"
    view_url = reverse_lazy("publishing:packaged-workbasket-queue-ui-list")

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
            url = self._promote_position(post.get("promote_position"))
        elif post.get("demote_position"):
            url = self._demote_position(post.get("demote_position"))
        elif post.get("promote_to_top_position"):
            url = self._promote_to_top_position(post.get("promote_to_top_position"))
        elif post.get("remove_from_queue"):
            url = self._remove_from_queue(post.get("remove_from_queue"))
        else:
            # Handle invalid post content by redisplaying the page.
            url = self.view_url

        return redirect(url)

    # Queue item position management.

    def _pause_queue(self, request):
        OperationalStatus.pause_queue(user=request.user)
        return self.view_url

    def _unpause_queue(self, request):
        OperationalStatus.unpause_queue(user=request.user)
        return self.view_url

    @atomic
    def _promote_position(self, pk):
        try:
            packaged_work_basket = PackagedWorkBasket.objects.select_for_update(
                nowait=True,
            ).get(pk=pk)
            packaged_work_basket.promote_position()
        except (
            PackagedWorkBasket.DoesNotExist,
            PackagedWorkBasketInvalidQueueOperation,
            OperationalError,
        ):
            # Nothing to do in the case of these exceptions.
            pass
        return self.view_url

    @atomic
    def _demote_position(self, pk):
        try:
            packaged_work_basket = PackagedWorkBasket.objects.select_for_update(
                nowait=True,
            ).get(pk=pk)
            packaged_work_basket.demote_position()
        except (
            PackagedWorkBasket.DoesNotExist,
            PackagedWorkBasketInvalidQueueOperation,
            OperationalError,
        ):
            # Nothing to do in the case of these exceptions.
            pass
        return self.view_url

    @atomic
    def _promote_to_top_position(self, pk):
        try:
            packaged_work_basket = PackagedWorkBasket.objects.select_for_update(
                nowait=True,
            ).get(pk=pk)
            packaged_work_basket.promote_to_top_position()
        except (
            PackagedWorkBasket.DoesNotExist,
            PackagedWorkBasketInvalidQueueOperation,
            OperationalError,
        ):
            # Nothing to do in the case of these exceptions.
            pass
        return self.view_url

    @atomic
    def _remove_from_queue(self, pk):
        try:
            packaged_work_basket = PackagedWorkBasket.objects.select_for_update(
                nowait=True,
            ).get(pk=pk)
            packaged_work_basket.abandon()
            return reverse(
                "workbaskets:workbasket-ui-changes",
                kwargs={"pk": packaged_work_basket.workbasket.pk},
            )
        except (
            PackagedWorkBasket.DoesNotExist,
            PackagedWorkBasketInvalidQueueOperation,
            TransitionNotAllowed,
            OperationalError,
        ):
            # Nothing to do in the case of these exceptions.
            return self.view_url


class EnvelopeQueueView(
    PermissionRequiredMixin,
    WithPaginationListMixin,
    ListView,
):
    """UI view used to download and manage envelope processing."""

    model = PackagedWorkBasket
    permission_required = "publishing.consume_from_packaging_queue"

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
        """
        Manage POST requests that signal the start of envelope processing.

        Valid and invalid POST requests alike redisplay the envelope queue view.
        """

        envelope_pk = request.POST.get("process_envelope")
        if envelope_pk:
            self._process_envelope(envelope_pk)

        return redirect(reverse("publishing:envelope-queue-ui-list"))

    @atomic
    def _process_envelope(self, pk):
        if not OperationalStatus.is_queue_paused():
            packaged_work_basket = PackagedWorkBasket.objects.select_for_update(
                nowait=True,
            ).get(pk=pk)
            try:
                packaged_work_basket.begin_processing()
            except (TransitionNotAllowed, OperationalError):
                # No error page right now, just reshow the list view.
                pass


class DownloadEnvelopeMixin:
    def download_response(self, envelope):
        """Returns a Respond object with associated payload containing the
        contents of `envelope.xml_file`."""

        file_content = envelope.xml_file.read()
        response = HttpResponse(file_content)
        response["content-type"] = "text/xml"
        response["content-length"] = len(file_content)
        response["content-disposition"] = (
            f'attachment; filename="{envelope.xml_file_name}"'
        )
        return response


class DownloadEnvelopeViewBase(DownloadEnvelopeMixin, DetailView):
    """View used to download an XML envelope."""

    model = PackagedWorkBasket

    def get(self, request, *args, **kwargs):
        packaged_workbasket = self.get_object()
        return self.download_response(packaged_workbasket.envelope)


class DownloadQueuedEnvelopeView(
    PermissionRequiredMixin,
    DownloadEnvelopeViewBase,
):
    permission_required = "publishing.consume_from_packaging_queue"

    def get(self, request, *args, **kwargs):
        packaged_workbasket = self.get_object()
        # Only permit downloading an envelope through this view if it is the one
        # currently being processed. This avoids accidentally downloading an
        # envelope that has already completed its processing step from a stale
        # page view.
        if packaged_workbasket != PackagedWorkBasket.objects.currently_processing():
            return redirect("publishing:envelope-queue-ui-list")
        return super().get(request, *args, **kwargs)


class DownloadAdminEnvelopeView(PermissionRequiredMixin, DownloadEnvelopeViewBase):
    permission_required = "publishing.manage_packaging_queue"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DownloadAdminLoadingReportView(PermissionRequiredMixin, DetailView):
    """View used to download a loading report."""

    permission_required = "publishing.manage_packaging_queue"
    model = LoadingReport

    def get(self, request, *args, **kwargs):
        loading_report = self.get_object()
        file_name = (
            loading_report.file_name if loading_report.file_name else "UNKNOWN_FILENAME"
        )
        content = loading_report.file.read()
        response = HttpResponse(content)
        response["content-length"] = len(content)
        response["content-type"] = get_mime_type(loading_report.file)
        response["content-disposition"] = f'attachment; filename="{file_name}"'

        return response


class CompleteEnvelopeProcessingView(PermissionRequiredMixin, CreateView):
    """Generic UI view used to confirm envelope processing."""

    permission_required = "publishing.consume_from_packaging_queue"
    template_name = "publishing/complete-envelope-processing.jinja"
    form_class = LoadingReportForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    @atomic
    def form_valid(self, form):
        """Create LoadingReport instance(s) associated with the
        PackagedWorkBasket and transition that PackagedWorkBasket instance to
        the next, completed processing state (either succeeded or failed)."""

        packaged_work_basket = PackagedWorkBasket.objects.get(
            pk=self.kwargs["pk"],
        )

        loading_reports = form.save(packaged_workbasket=packaged_work_basket)

        self.transition_packaged_work_basket(packaged_work_basket)
        return redirect(self.get_success_url())

    def transition_packaged_work_basket(self, packaged_work_basket):
        raise NotImplementedError()


class EnvelopeActionConfirmView(DetailView):
    permission_required = "publishing.consume_from_packaging_queue"
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

        data["page_title"] = "Accept envelope confirmation"
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

        data["page_title"] = "Reject envelope confirmation"
        data["message"] = f"Envelope ID {envelope.envelope_id} has been rejected."
        return data


class PackagedWorkbasketCreateView(PermissionRequiredMixin, CreateView):
    """UI endpoint for creating packaged workbaskets."""

    permission_required = "publishing.manage_packaging_queue"
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
                "workbaskets:current-workbasket",
            )
        except TransitionNotAllowed as err:
            self.logger.error(
                "Error: %s \n Redirecting to work basket %s summary",
                err,
                self.workbasket.id,
            )
            return redirect(
                "workbaskets:current-workbasket",
            )

        queued_wb = None
        try:
            queued_wb = PackagedWorkBasket.objects.create(
                workbasket=wb,
                **form.cleaned_data,
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
                "workbaskets:current-workbasket",
            )

        return redirect(
            "publishing:packaged-workbasket-queue-confirm-create",
            pk=queued_wb.pk,
        )


class PackagedWorkbasketConfirmCreate(DetailView):
    permission_required = "publishing.manage_packaging_queue"
    template_name = "publishing/confirm_create.jinja"
    model = PackagedWorkBasket

    def get_queryset(self):
        """Return package work basket based on packaged workbasket pk."""
        return PackagedWorkBasket.objects.filter(
            id=self.kwargs.get("pk"),
        )


class EnvelopeListFilter(TamatoFilter):
    search_fields = ("envelope_id",)
    clear_url = reverse_lazy("publishing:envelope-list-ui-list")

    class Meta:
        model = Envelope
        fields = ["search"]


class EnvelopeListView(
    PermissionRequiredMixin,
    WithPaginationListView,
):
    """UI view used to view processed (accepted / published and rejected)
    envelopes."""

    permission_required = "publishing.view_envelope"
    template_name = "publishing/envelope_list.jinja"
    filterset_class = EnvelopeListFilter
    search_fields = [
        "title",
        "reason",
    ]

    def get_queryset(self):
        return Envelope.objects.successfully_processed().reverse()


class EnvelopeFileHistoryView(
    PermissionRequiredMixin,
    WithPaginationListMixin,
    ListView,
):
    """UI view used to list the XML file history of a published envelope and its
    previously rejected envelopes (if any)."""

    permission_required = "publishing.view_envelope"
    template_name = "publishing/envelope_file_history.jinja"

    def get_published_envelope(self):
        """Get the published envelope instance for the envelope ID (as given by
        the `envelope_id` captured parameter)."""
        return Envelope.objects.successfully_processed().get(
            envelope_id=self.kwargs["envelope_id"],
        )

    def get_queryset(self):
        return self.get_published_envelope().get_versions()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["xml_file_name"] = self.get_published_envelope().xml_file_name
        return data


class DownloadEnvelopeView(
    DownloadEnvelopeMixin,
    PermissionRequiredMixin,
    BaseDetailView,
):
    """UI view to download a processed (succeeded or failed) envelope file."""

    permission_required = "publishing.view_envelope"

    def get_queryset(self):
        return Envelope.objects.processed()

    def get(self, request, *args, **kwargs):
        return self.download_response(self.get_object())
