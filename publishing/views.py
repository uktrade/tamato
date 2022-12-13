from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView
from django_fsm import TransitionNotAllowed

from common.views import WithPaginationListMixin
from publishing.models import PackagedWorkBasket
from publishing.models import PackagedWorkBasketInvalidQueueOperation
from publishing.models import ProcessingState


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

        return HttpResponseRedirect(url)

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
            TransitionNotAllowed,
            PackagedWorkBasketInvalidQueueOperation,
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
