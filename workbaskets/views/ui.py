import logging
import re
from datetime import date
from functools import cached_property
from typing import Tuple
from urllib.parse import urlencode

import boto3
import django_filters
import kombu
from botocore.client import Config
from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import F
from django.db.models import ProtectedError
from django.db.models import Q
from django.db.transaction import atomic
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django_filters import FilterSet
from markdownify import markdownify

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from checks.models import TrackedModelCheck
from common.filters import TamatoFilter
from common.inspect_tap_tasks import TAPTasks
from common.models import Transaction
from common.models.transactions import TransactionPartition
from common.util import format_date_string
from common.views import SortingMixin
from common.views import WithPaginationListMixin
from common.views import WithPaginationListView
from common.views import build_pagination_list
from exporter.models import Upload
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from importer.goods_report import GoodsReporter
from measures.models import Measure
from notifications.models import Notification
from notifications.models import NotificationTypeChoices
from publishing.models import PackagedWorkBasket
from quotas.models import QuotaAssociation
from quotas.models import QuotaBlocking
from quotas.models import QuotaDefinition
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaSuspension
from regulations.models import Regulation
from tasks.models import Comment
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskAssignee
from workbaskets import forms
from workbaskets.models import DataRow
from workbaskets.models import DataUpload
from workbaskets.models import WorkBasket
from workbaskets.session_store import SessionStore
from workbaskets.tasks import call_check_workbasket_sync
from workbaskets.validators import WorkflowStatus
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.mixins import WithCurrentWorkBasket

logger = logging.getLogger(__name__)

User = get_user_model()


class WorkBasketFilter(TamatoFilter):
    search_fields = (
        "id",
        "author",
        "reason",
        "title",
    )
    clear_url = reverse_lazy("workbaskets:workbasket-ui-list-all")

    class Meta:
        model = WorkBasket
        fields = ["search", "status"]


class WorkBasketAssignmentFilter(FilterSet):
    """Filter a workbasket queryset based on different assignment
    possibilities."""

    def assignment_filter(self, queryset, name, value):
        active_workers = (
            TaskAssignee.objects.workbasket_workers()
            .assigned()
            .values_list("task__workbasket_id")
        )
        active_reviewers = (
            TaskAssignee.objects.workbasket_reviewers()
            .assigned()
            .values_list("task__workbasket_id")
        )
        if value == "Full":
            return queryset.filter(
                Q(id__in=active_workers) & Q(id__in=active_reviewers),
            )
        elif value == "Reviewer":
            return queryset.filter(id__in=active_reviewers)
        elif value == "Worker":
            return queryset.filter(id__in=active_workers)
        elif value == "Awaiting":
            return queryset.filter(
                ~Q(id__in=active_workers) & ~Q(id__in=active_reviewers),
            )
        else:
            return queryset

    assignment = django_filters.CharFilter(method="assignment_filter")

    class Meta:
        model = WorkBasket
        fields = ["assignment"]


class WorkBasketConfirmCreate(DetailView):
    template_name = "workbaskets/confirm_create.jinja"
    model = WorkBasket
    queryset = WorkBasket.objects.all()


class WorkBasketCreate(PermissionRequiredMixin, CreateView):
    """UI endpoint for creating workbaskets."""

    permission_required = "workbaskets.add_workbasket"
    template_name = "workbaskets/create.jinja"
    form_class = forms.WorkbasketCreateForm

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            return redirect(reverse("login"))
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        self.object.save()
        self.object.set_as_current(self.request.user)
        return redirect(
            reverse(
                "workbaskets:workbasket-ui-confirm-create",
                kwargs={"pk": self.object.pk},
            ),
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class WorkBasketUpdate(PermissionRequiredMixin, UpdateView):
    """UI endpoint for updating a workbasket's title and description."""

    permission_required = "workbaskets.add_workbasket"
    template_name = "workbaskets/edit-details.jinja"
    form_class = forms.WorkbasketUpdateForm
    model = WorkBasket

    def get_success_url(self):
        return reverse(
            "workbaskets:workbasket-ui-confirm-update",
            kwargs={"pk": self.object.pk},
        )


class WorkBasketConfirmUpdate(DetailView):
    template_name = "workbaskets/confirm_update.jinja"
    model = WorkBasket


class SelectWorkbasketView(PermissionRequiredMixin, WithPaginationListView):
    """UI endpoint for viewing and filtering workbaskets."""

    filterset_class = WorkBasketAssignmentFilter
    template_name = "workbaskets/select-workbasket.jinja"
    permission_required = "workbaskets.change_workbasket"

    def get_queryset(self):
        return (
            WorkBasket.objects.exclude(status=WorkflowStatus.PUBLISHED)
            .exclude(status=WorkflowStatus.ARCHIVED)
            .exclude(status=WorkflowStatus.QUEUED)
            .exclude_importing_imports()
            .exclude_failed_imports()
            .order_by("-updated_at")
        )

    def post(self, request, *args, **kwargs):
        workbasket_pk = request.POST.get("workbasket")
        workbasket_tab = request.POST.get("workbasket-tab")

        workbasket_tab_map = {
            "view-summary": {
                "path_name": "workbaskets:current-workbasket",
                "kwargs": {},
            },
            "add-edit-items": {
                "path_name": "workbaskets:edit-workbasket",
                "kwargs": {},
            },
            "view-violations": {
                "path_name": "workbaskets:workbasket-ui-violations",
                "kwargs": {},
            },
            "review-measures": {
                "path_name": "workbaskets:workbasket-ui-review-measures",
                "kwargs": {"pk": workbasket_pk},
            },
            "review-goods": {
                "path_name": "workbaskets:workbasket-ui-review-goods",
                "kwargs": {"pk": workbasket_pk},
            },
        }

        workbasket = WorkBasket.objects.get(pk=workbasket_pk) if workbasket_pk else None

        if workbasket:
            if workbasket.status == WorkflowStatus.ERRORED:
                workbasket.restore()
                workbasket.save()

            workbasket.set_as_current(request.user)

            if workbasket_tab:
                view = workbasket_tab_map[workbasket_tab]
                return redirect(reverse(view["path_name"], kwargs=view["kwargs"]))
            else:
                return redirect(reverse("workbaskets:current-workbasket"))

        return redirect(reverse("workbaskets:workbasket-ui-list"))


class WorkBasketChangesDelete(PermissionRequiredMixin, ListView):
    """UI for user review of WorkBasket item deletion."""

    template_name = "workbaskets/delete_changes.jinja"
    permission_required = "workbaskets.change_workbasket"

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    def _session_store(self, workbasket):
        """Get the current user's SessionStore for the WorkBasket that they're
        deleting, containing ids of the items that have been selected for
        deletion."""

        return SessionStore(
            self.request,
            f"WORKBASKET_SELECTIONS_{workbasket.pk}",
        )

    def get_queryset(self):
        """Get TrackedModelQuerySet of instances that are candidates for
        deletion."""

        store = self._session_store(self.workbasket)
        pks = [
            forms.SelectableObjectsForm.object_id_from_field_name(k)
            for k in store.data.keys()
        ]
        return self.workbasket.tracked_models.filter(pk__in=pks)

    def post(self, request, *args, **kwargs):
        if request.POST.get("action", None) != "delete":
            # The user has cancelled out of the deletion process.
            if self.workbasket == WorkBasket.current(self.request):
                return redirect("workbaskets:current-workbasket")
            else:
                return redirect(
                    "workbaskets:workbasket-ui-changes",
                    pk=self.workbasket.pk,
                )

        # By reverse ordering on record_code + subrecord_code we're able to
        # delete child entities first, avoiding protected foreign key
        # violations.
        object_list = self.get_queryset().record_ordering().reverse()

        for obj in object_list:
            # Unlike situations where TrackedModels are superceded and are
            # subject to UpdateType.DELETE, WorkBasket item deletion really
            # should remove rows from the DB.
            try:
                obj.delete()
            except ProtectedError:
                # TODO Capture deletion failure and present back to UI.
                # UI component(s) design in the backlog for this: TP-1148.
                pass

        # Removing TrackedModel instances from the workbasket may result in
        # empty Transaction instances, so remove those from the workbasket too.
        self.workbasket.purge_empty_transactions()

        session_store = self._session_store(self.workbasket)
        session_store.clear()

        redirect_url = reverse(
            "workbaskets:workbasket-ui-changes-confirm-delete",
            kwargs={"pk": self.workbasket.pk},
        )
        return redirect(redirect_url)


class WorkBasketChangesConfirmDelete(TemplateView):
    template_name = "workbaskets/delete_changes_confirm.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_workbasket"] = WorkBasket.current(self.request)
        context["view_workbasket"] = WorkBasket.objects.get(pk=self.kwargs["pk"])
        return context


def download_envelope(request):
    """
    Creates s3 resource using AWS environment variables.

    Tries to get filename from most recent s3 upload. If no upload exists,
    returns 404.

    Generates presigned url from s3 client using bucket and file names.

    Returns `HttpResponseRedirect` with presigned url passed as only argument.
    """
    s3 = boto3.resource(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )

    try:
        last_added = (
            settings.HMRC_STORAGE_DIRECTORY
            + Upload.objects.latest("created_date").filename
        )
    except Upload.DoesNotExist as err:
        raise Http404("No uploaded envelope available for download")

    url = s3.meta.client.generate_presigned_url(
        ClientMethod="get_object",
        ExpiresIn=3600,
        Params={
            "Bucket": settings.HMRC_STORAGE_BUCKET_NAME,
            "Key": last_added,
        },
    )

    return HttpResponseRedirect(url)


@method_decorator(require_current_workbasket, name="dispatch")
class EditWorkbasketView(PermissionRequiredMixin, TemplateView):
    template_name = "workbaskets/edit-workbasket.jinja"
    permission_required = "workbaskets.change_workbasket"


@method_decorator(require_current_workbasket, name="dispatch")
class CurrentWorkBasket(FormView):
    template_name = "workbaskets/summary-workbasket.jinja"
    form_class = forms.WorkBasketCommentCreateForm

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    @cached_property
    def comments(self):
        ordering = self.get_comments_ordering()[0]
        return Comment.objects.filter(task__workbasket=self.workbasket).order_by(
            ordering,
        )

    @cached_property
    def paginator(self):
        return Paginator(self.comments, per_page=20)

    def get_comments_ordering(self) -> Tuple[str, str]:
        """Returns the ordering for `self.comments` based on `ordered` GET param
        together with the title to use for the sort by filter (which will be the
        opposite of the applied ordering)."""
        ordered = self.request.GET.get("ordered")
        if ordered == "desc":
            ordering = "created_at"
            new_sort_by_title = "Newest first"
        else:
            ordering = "-created_at"
            new_sort_by_title = "Oldest first"
        return ordering, new_sort_by_title

    def form_valid(self, form):
        form.save(user=self.request.user, workbasket=self.workbasket)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("workbaskets:current-workbasket")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        assigned_workers = [
            {"pk": user.pk, "name": user.user.get_full_name()}
            for user in self.workbasket.worker_assignments.order_by(
                "user__first_name",
                "user__last_name",
            )
        ]

        assigned_reviewers = [
            {"pk": user.pk, "name": user.user.get_full_name()}
            for user in self.workbasket.reviewer_assignments.order_by(
                "user__first_name",
                "user__last_name",
            )
        ]

        users = (
            User.objects.filter(
                Q(groups__name__in=["Tariff Managers", "Tariff Lead Profile"])
                | Q(is_superuser=True),
            )
            .filter(is_active=True)
            .distinct()
            .order_by("first_name", "last_name")
        )
        assignable_users = [
            {"pk": user.pk, "name": user.get_full_name()} for user in users
        ]

        can_add_comment = self.request.user.has_perm("tasks.add_comment")
        can_view_comment = self.request.user.has_perm("tasks.view_comment")

        page = self.paginator.get_page(self.request.GET.get("page", 1))
        page_links = build_pagination_list(
            page.number,
            self.paginator.num_pages,
        )

        context.update(
            {
                "workbasket": self.workbasket,
                "assigned_workers": assigned_workers,
                "assigned_reviewers": assigned_reviewers,
                "assignable_users": assignable_users,
                "can_add_comment": can_add_comment,
                "can_view_comment": can_view_comment,
                "comments": page.object_list,
                "sort_by_title": self.get_comments_ordering()[1],
                "paginator": self.paginator,
                "page_obj": page,
                "page_links": page_links,
            },
        )

        return context


class WorkBasketList(PermissionRequiredMixin, WithPaginationListView):
    """UI endpoint for viewing and filtering workbaskets."""

    template_name = "workbaskets/list.jinja"
    permission_required = "workbaskets.view_workbasket"
    filterset_class = WorkBasketFilter
    search_fields = [
        "title",
        "reason",
    ]

    def get_queryset(self):
        return WorkBasket.objects.order_by("-updated_at")


class WorkBasketDetailView(PermissionRequiredMixin, DetailView):
    """UI endpoint for viewing a specified workbasket."""

    model = WorkBasket
    template_name = "workbaskets/detail.jinja"
    permission_required = "workbaskets.view_workbasket"


class WorkBasketChangesView(SortingMixin, PermissionRequiredMixin, FormView):
    """UI endpoint for viewing changes in a workbasket."""

    permission_required = "workbaskets.view_workbasket"
    template_name = "workbaskets/changes.jinja"
    form_class = forms.SelectableObjectsForm
    paginate_by = 100

    form_action_redirect_map = {
        "remove-selected": "workbaskets:workbasket-ui-changes-delete",
        "remove-all": "workbaskets:workbasket-ui-changes-delete",
        "page-prev": "workbaskets:workbasket-ui-changes",
        "page-next": "workbaskets:workbasket-ui-changes",
    }

    sort_by_fields = ["component", "action", "activity_date"]
    custom_sorting = {
        "component": "polymorphic_ctype",
        "action": "update_type",
        "activity_date": "transaction__updated_at",
    }

    @cached_property
    def workbasket(self):
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    @property
    def paginator(self):
        return Paginator(
            self.get_queryset(),
            per_page=self.paginate_by,
        )

    def get_queryset(self):
        queryset = (
            self.workbasket.tracked_models.with_transactions_and_models().order_by(
                "transaction__order",
                "pk",
            )
        )
        ordering = self.get_ordering()
        if ordering:
            ordering = (ordering, "transaction")
            return queryset.order_by(*ordering)
        else:
            return queryset

    def get_initial(self):
        store = SessionStore(
            self.request,
            f"WORKBASKET_SELECTIONS_{self.workbasket.pk}",
        )
        return store.data.copy()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        kwargs["objects"] = page.object_list
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        page_links = build_pagination_list(
            page.number,
            self.paginator.num_pages,
        )
        user_can_delete_items = (
            self.request.user.is_superuser
            or self.request.user.has_perm("workbaskets.change_workbasket")
        )
        user_can_delete_workbasket = (
            self.request.user.is_superuser
            or self.request.user.has_perm("workbaskets.delete_workbasket")
        )
        context.update(
            {
                "workbasket": self.workbasket,
                "page_obj": page,
                "page_links": page_links,
                "paginator": self.paginator,
                "user_can_delete_items": user_can_delete_items,
                "user_can_delete_workbasket": user_can_delete_workbasket,
            },
        )
        return context

    def _append_url_params(self, url, form_action):
        if form_action in ["remove-selected", "remove-all"]:
            return url

        page_number = int(self.request.GET.get("page", 1))
        page = self.paginator.get_page(page_number)
        if form_action == "page-prev":
            page_number = page.previous_page_number()
        elif form_action == "page-next":
            page_number = page.next_page_number()

        sort_by = self.request.GET.get("sort_by", None)
        ordered = self.request.GET.get("ordered", None)
        if sort_by and ordered:
            return f"{url}?page={page_number}&sort_by={sort_by}&ordered={ordered}"
        else:
            return f"{url}?page={page_number}"

    def form_valid(self, form):
        store = SessionStore(
            self.request,
            f"WORKBASKET_SELECTIONS_{self.workbasket.pk}",
        )
        form_action = self.request.POST.get("form-action")
        store.remove_items(form.cleaned_data)
        if form_action == "remove-all":
            object_list = {
                self.form_class.field_name_for_object(obj): True
                for obj in self.workbasket.tracked_models
            }
            store.add_items(object_list)
        else:
            to_add = {key: value for key, value in form.cleaned_data.items() if value}
            store.add_items(to_add)
        return super().form_valid(form)

    def get_success_url(self):
        form_action = self.request.POST.get("form-action")
        try:
            return self._append_url_params(
                reverse(
                    self.form_action_redirect_map[form_action],
                    kwargs={"pk": self.workbasket.pk},
                ),
                form_action,
            )
        except KeyError:
            return reverse(
                "workbaskets:workbasket-ui-detail",
                kwargs={"pk": self.workbasket.pk},
            )


class WorkBasketTransactionOrderView(PermissionRequiredMixin, FormView):
    """UI endpoint for reordering transactions in a workbasket."""

    permission_required = "workbaskets.view_workbasket"
    template_name = "workbaskets/transaction_order.jinja"
    form_class = forms.SelectableObjectsForm
    paginate_by = 100

    form_action_redirect_map = {
        "page-prev": "workbaskets:workbasket-ui-transaction-order",
        "page-next": "workbaskets:workbasket-ui-transaction-order",
        "move-transaction": "workbaskets:workbasket-ui-transaction-order",
    }

    @property
    def form_action_mapping(self):
        """A dictionary mapping form actions to transaction reordering
        functions."""
        return {
            # Selected transactions
            "promote-transactions-top": self.promote_transaction_to_top,
            "demote-transactions-bottom": self.demote_transaction_to_bottom,
            "promote-transactions": self.promote_transaction,
            "demote-transactions": self.demote_transaction,
            # Individual transaction
            "promote-transaction-top": self.promote_transaction_to_top,
            "demote-transaction-bottom": self.demote_transaction_to_bottom,
            "promote-transaction": self.promote_transaction,
            "demote-transaction": self.demote_transaction,
        }

    @cached_property
    def workbasket(self):
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    @property
    def paginator(self):
        return Paginator(
            self.workbasket.transactions.prefetch_related("tracked_models"),
            per_page=self.paginate_by,
        )

    @property
    def session_store(self):
        """Get the session store containing form field ids of the transactions
        selected in the workbasket."""
        return SessionStore(
            self.request,
            f"TRANSACTION_SELECTIONS_{self.workbasket.pk}",
        )

    def store_transaction_selections(self, form):
        """Add the selected transactions in the form to the session store."""
        session_store = self.session_store
        session_store.remove_items(form.cleaned_data)
        to_add = {key: value for key, value in form.cleaned_data.items() if value}
        session_store.add_items(to_add)

    def get_queryset(self):
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        queryset = page.object_list
        return queryset

    def get_initial(self):
        return self.session_store.data.copy()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["objects"] = self.get_queryset()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        page_links = build_pagination_list(
            page.number,
            self.paginator.num_pages,
        )
        user_can_move_transactions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("workbaskets.change_workbasket")
        )
        context.update(
            {
                "workbasket": self.workbasket,
                "page_obj": page,
                "page_links": page_links,
                "paginator": self.paginator,
                "user_can_move_transactions": user_can_move_transactions,
                "first_transaction_in_workbasket": self.first_transaction_in_workbasket,
                "last_transaction_in_workbasket": self.last_transaction_in_workbasket,
            },
        )
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if not form.is_valid():
            return self.form_invalid(form)

        self.store_transaction_selections(form)

        form_action = form.data.get("form-action", "")
        if "transactions" in form_action:
            return self.move_selected_transactions(form_action)
        elif "transaction" in form_action:
            return self.move_transaction(form_action)
        else:
            return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        form_action = self.request.POST.get("form-action")
        if form_action.startswith("promote") or form_action.startswith(
            "demote",
        ):
            form_action = "move-transaction"
        try:
            return self._append_page_url_param(
                reverse(
                    self.form_action_redirect_map[form_action],
                    kwargs={"pk": self.workbasket.pk},
                ),
                form_action,
            )
        except KeyError:
            return reverse(
                "workbaskets:workbasket-ui-detail",
                kwargs={"pk": self.workbasket.pk},
            )

    def _append_page_url_param(self, url, form_action):
        """Append a page number parameter to the URL."""
        page_number = int(self.request.GET.get("page", 1))
        page = self.paginator.get_page(page_number)
        if form_action == "page-prev":
            page_number = page.previous_page_number()
        elif form_action == "page-next":
            page_number = page.next_page_number()
        return f"{url}?page={page_number}"

    def workbasket_transactions(self):
        """Returns the current workbasket's transactions ordered by `order`,
        while guarding against non-editing status on workbasket to minimise
        chances of mishap."""
        return Transaction.objects.filter(
            workbasket=self.workbasket,
            workbasket__status=WorkflowStatus.EDITING,
        ).order_by("order")

    def _get_transaction_pk_from_form_action(self, form_action):
        """
        Extract a primary key value from the form_action string value.

        See the `regex_pattern` attribute in this function for valid formats.
        """
        regex_pattern = "(promote-transaction-top|promote-transaction|demote-transaction|demote-transaction-bottom)__([0-9]+)"
        try:
            pk = int(re.search(regex_pattern, form_action).group(2))
        except AttributeError:
            logger.error(
                f"Invalid form_action format, {form_action}, must match the "
                f"regular expression pattern '{regex_pattern}'.",
            )
            return None

        try:
            # Guard against referencing transactions that are in anything other
            # than the DRAFT partition and which are additionally in the
            # current workbasket, which must be in EDITING status - DRAFT
            # should also imply this state.
            return Transaction.objects.get(
                workbasket=self.workbasket,
                workbasket__status=WorkflowStatus.EDITING,
                partition=TransactionPartition.DRAFT,
                pk=pk,
            )
        except ObjectDoesNotExist:
            logger.error(
                f"Invalid transaction key in form_action, {form_action}",
            )
            return None

    def move_selected_transactions(self, form_action):
        """
        Reorder the transactions in the session store according to
        `form_action`.

        Note that transaction reordering necessitates a new business rules
        check.
        """

        transaction_pks = [
            forms.SelectableObjectsForm.object_id_from_field_name(key)
            for key in self.session_store.data.keys()
        ]
        self.session_store.clear()

        if (
            form_action == "promote-transactions-top"
            or form_action == "demote-transactions"
        ):
            # Reverse to keep the selected transactions in their relative order in the final reordering.
            transaction_pks.reverse()

        for pk in transaction_pks:
            selected_transaction = self.workbasket_transactions().filter(pk=pk).last()
            self.form_action_mapping[form_action](selected_transaction)

        self.workbasket.delete_checks()

        return HttpResponseRedirect(self.get_success_url())

    def move_transaction(self, form_action):
        """
        Reorder the individual transaction in `form_action` according to
        `form_action`.

        Note that transaction reordering necessitates a new business rules
        check.
        """

        self.session_store.clear()
        transaction = self._get_transaction_pk_from_form_action(form_action)
        form_action = form_action.split("__")[0]
        self.form_action_mapping[form_action](transaction)
        self.workbasket.delete_checks()

        return HttpResponseRedirect(self.get_success_url())

    @atomic
    def promote_transaction_to_top(self, promoted_transaction):
        """Set the transaction order of `promoted_transaction` to be first in
        the workbasket, demoting the transactions that came before it."""

        top_transaction = self.workbasket_transactions().first()

        if (
            not promoted_transaction
            or not top_transaction
            or promoted_transaction == top_transaction
        ):
            return

        current_position = promoted_transaction.order
        top_position = top_transaction.order

        self.workbasket_transactions().filter(order__lt=current_position).update(
            order=F("order") + 1,
        )

        promoted_transaction.order = top_position
        promoted_transaction.save(update_fields=["order"])

    @atomic
    def demote_transaction_to_bottom(self, demoted_transaction):
        """Set the transaction order of `demoted_transaction` to be last in the
        workbasket, promoting the transactions that came after it."""

        bottom_transaction = self.workbasket_transactions().last()

        if (
            not demoted_transaction
            or not bottom_transaction
            or demoted_transaction == bottom_transaction
        ):
            return

        current_position = demoted_transaction.order
        bottom_position = bottom_transaction.order

        self.workbasket_transactions().filter(order__gt=current_position).update(
            order=F("order") - 1,
        )

        demoted_transaction.order = bottom_position
        demoted_transaction.save(update_fields=["order"])

    @atomic
    def promote_transaction(self, promoted_transaction):
        """Swap the transaction order of `promoted_transaction` with the
        (demoted) transaction above it."""

        demoted_transaction = (
            self.workbasket_transactions()
            .filter(
                order__lt=promoted_transaction.order,
            )
            .last()
        )
        if not promoted_transaction or not demoted_transaction:
            return

        promoted_transaction.order, demoted_transaction.order = (
            demoted_transaction.order,
            promoted_transaction.order,
        )
        Transaction.objects.bulk_update(
            [promoted_transaction, demoted_transaction],
            ["order"],
        )

    @atomic
    def demote_transaction(self, demoted_transaction):
        """Swap the transaction order of `demoted_transaction` with the
        (promoted) transaction below it."""

        promoted_transaction = (
            self.workbasket_transactions()
            .filter(
                order__gt=demoted_transaction.order,
            )
            .first()
        )
        if not demoted_transaction or not promoted_transaction:
            return

        demoted_transaction.order, promoted_transaction.order = (
            promoted_transaction.order,
            demoted_transaction.order,
        )
        Transaction.objects.bulk_update(
            [demoted_transaction, promoted_transaction],
            ["order"],
        )

    @cached_property
    def first_transaction_in_workbasket(self):
        return self.workbasket_transactions().first()

    @cached_property
    def last_transaction_in_workbasket(self):
        return self.workbasket_transactions().last()


@method_decorator(require_current_workbasket, name="dispatch")
class WorkBasketViolations(SortingMixin, WithPaginationListView):
    """UI endpoint for viewing the current workbasket's business rule
    violations."""

    model = TrackedModelCheck
    template_name = "workbaskets/violations.jinja"
    paginate_by = 50
    sort_by_fields = ["model", "date", "check_name"]
    custom_sorting = {
        "date": "transaction_check__transaction__created_at",
        "model": "model__polymorphic_ctype",
    }

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(workbasket=self.workbasket, **kwargs)
        if self.workbasket.rule_check_task_id:
            result = AsyncResult(self.workbasket.rule_check_task_id)
            if result.status != "SUCCESS":
                context["rule_check_in_progress"] = True
            else:
                context["rule_check_in_progress"] = False

        return context

    def get_queryset(self):
        self.queryset = TrackedModelCheck.objects.filter(
            transaction_check__transaction__workbasket=self.workbasket,
            successful=False,
        )
        return super().get_queryset()

    @property
    def paginator(self):
        return Paginator(
            self.get_queryset(),
            per_page=50,
        )


class WorkBasketViolationDetail(DetailView):
    """UI endpoint for viewing a specified workbasket's business rule
    violations."""

    model = TrackedModelCheck
    template_name = "workbaskets/violation_detail.jinja"

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    def get_context_data(self, **kwargs):
        return super().get_context_data(workbasket=self.workbasket, **kwargs)

    def override_violation(self):
        """
        Override the `TrackedModelCheck` instance for this rules check
        violation, setting its `successful` value to True.

        If there are no other failing `TrackedModelCheck` instances on the
        associated `TransactionCheck` instance, then also set its `successful`
        value to True.
        """
        model_check = self.get_object()
        model_check.successful = True
        model_check.save()

        transaction_check = model_check.transaction_check
        # Only clear the associated transcation check if model_check
        # was the last and only other failing model check.
        other_model_checks = transaction_check.model_checks.filter(successful=False)
        if not other_model_checks:
            transaction_check.successful = True
            transaction_check.save()

    def post(self, request, *args, **kwargs):
        if request.POST.get("action", None) == "delete" and request.user.is_superuser:
            self.override_violation()

        return redirect("workbaskets:workbasket-ui-violations")


class WorkBasketDelete(PermissionRequiredMixin, DeleteView):
    """
    UI to confirm (or cancel) workbasket deletion.

    Rather than using the current workbasket to identify the target workbasket
    for deletion, it is identified by its primary key as a URL captured param.
    This reduces the chances of deleting the wrong workbasket.
    """

    form_class = forms.WorkbasketDeleteForm
    model = WorkBasket
    permission_required = "workbaskets.delete_workbasket"
    template_name = "workbaskets/delete_workbasket.jinja"

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["workbasket"] = self.workbasket
        return context

    def get_success_url(self) -> str:
        return reverse(
            "workbaskets:workbasket-ui-delete-done",
            kwargs={"deleted_pk": self.kwargs["pk"]},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def form_valid(self, form):
        if (
            PackagedWorkBasket.objects.filter(workbasket=self.object).exists()
            or self.object.tasks.exists()
        ):
            self.object.archive()
            self.object.save()
        else:
            self.object.delete()
        return redirect(self.get_success_url())


class WorkBasketDeleteDone(TemplateView):
    """
    UI presented after successfully deleting a workbasket.

    The deleted workbasket's primary key is identified via the `deleted_pk`
    captured param, distinguishing it from the typical `pk` identifier - since
    the object has been deleted and the PK therefore no longer exists.
    """

    template_name = "workbaskets/delete_workbasket_done.jinja"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["deleted_pk"] = self.kwargs["deleted_pk"]
        return context_data


class WorkBasketCompare(WithCurrentWorkBasket, FormView):
    success_url = reverse_lazy("workbaskets:workbasket-check-ui-compare")
    template_name = "workbaskets/compare.jinja"
    form_class = forms.WorkbasketCompareForm

    @property
    def workbasket_measures(self):
        return self.workbasket.measures.all()

    @property
    def data_upload(self):
        try:
            return DataUpload.objects.get(workbasket=self.workbasket)
        except DataUpload.DoesNotExist:
            return None

    def form_valid(self, form):
        try:
            existing = DataUpload.objects.get(workbasket=self.workbasket)
            existing.raw_data = form.cleaned_data["raw_data"]
            existing.rows.all().delete()
            for row in form.cleaned_data["data"]:
                DataRow.objects.create(
                    valid_between=row.valid_between,
                    duty_sentence=row.duty_sentence,
                    commodity=row.commodity,
                    data_upload=existing,
                )
            existing.save()
        except DataUpload.DoesNotExist:
            data_upload = DataUpload.objects.create(
                raw_data=form.cleaned_data["raw_data"],
                workbasket=self.workbasket,
            )
            for row in form.cleaned_data["data"]:
                DataRow.objects.create(
                    valid_between=row.valid_between,
                    duty_sentence=row.duty_sentence,
                    commodity=row.commodity,
                    data_upload=data_upload,
                )
        return super().form_valid(form)

    @property
    def matching_measures(self):
        measures = []
        if self.data_upload:
            for row in self.data_upload.rows.all():
                matches = self.workbasket_measures.filter(
                    valid_between=row.valid_between,
                    goods_nomenclature__item_id=row.commodity,
                )
                duty_matches = [
                    measure
                    for measure in matches
                    if measure.duty_sentence == row.duty_sentence
                ]
                measures += duty_matches
        return measures

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(
            workbasket=self.workbasket,
            data_upload=self.data_upload,
            matching_measures=self.matching_measures,
            *args,
            **kwargs,
        )


@method_decorator(require_current_workbasket, name="dispatch")
class WorkBasketChecksView(FormView):
    template_name = "workbaskets/checks.jinja"
    form_class = forms.SelectableObjectsForm

    # Form action mappings to URL names.
    action_success_url_names = {
        "run-business-rules": "workbaskets:workbasket-checks",
        "terminate-rule-check": "workbaskets:workbasket-checks",
        "page-prev": "workbaskets:workbasket-checks",
        "page-next": "workbaskets:workbasket-checks",
    }

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    @atomic
    def run_business_rules(self):
        """Remove old checks, start new checks via a Celery task and save the
        newly created task's ID on the workbasket."""
        workbasket = self.workbasket
        workbasket.delete_checks()
        task = call_check_workbasket_sync.apply_async(
            (workbasket.pk,),
            countdown=1,
        )
        logger.info(
            f"Started rule check against workbasket.id={workbasket.pk} "
            f"on task.id={task.id}",
        )
        workbasket.rule_check_task_id = task.id
        workbasket.save()

    def get_success_url(self):
        form_action = self.request.POST.get("form-action")
        if form_action == "run-business-rules":
            self.run_business_rules()
        elif form_action == "terminate-rule-check":
            self.workbasket.terminate_rule_check()
        return reverse("workbaskets:workbasket-checks")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # set to true if there is an associated goods import batch with an unsent notification
        try:
            import_batch = self.workbasket.importbatch
            unsent_notifcation = (
                import_batch
                and import_batch.goods_import
                and not Notification.objects.filter(
                    notified_object_pk=import_batch.pk,
                    notification_type=NotificationTypeChoices.GOODS_REPORT,
                ).exists()
            )
        except ObjectDoesNotExist:
            unsent_notifcation = False
        context.update(
            {
                "workbasket": self.workbasket,
                "rule_check_in_progress": False,
                "unsent_notification": unsent_notifcation,
            },
        )
        if self.workbasket.rule_check_task_id:
            result = AsyncResult(self.workbasket.rule_check_task_id)
            if result.status != "SUCCESS":
                context.update({"rule_check_in_progress": True})
            else:
                self.workbasket.set_as_current(self.request.user)

            num_completed, total = self.workbasket.rule_check_progress()
            context.update(
                {
                    "rule_check_progress": f"Completed {num_completed} out of {total} checks",
                },
            )

        return context


class WorkBasketReviewView(PermissionRequiredMixin, WithPaginationListView):
    """Base view from which nested workbasket review tab views inherit."""

    template_name = "workbaskets/review.jinja"
    filterset_fields = ["update_type"]
    paginate_by = 30
    permission_required = "workbaskets.view_workbasket"

    @property
    def workbasket(self):
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    def get_queryset(self):
        return self.model.objects.filter(
            transaction__workbasket=self.workbasket,
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["user_workbasket"] = WorkBasket.current(self.request)
        context["workbasket"] = self.workbasket
        return context


class WorkBasketReviewAdditionalCodesView(WorkBasketReviewView):
    """UI endpoint for reviewing additional code changes in a workbasket."""

    model = AdditionalCode

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review additional codes"
        context["selected_tab"] = "additional-codes"
        context["tab_template"] = "includes/additional_codes/list.jinja"
        return context


class WorkBasketReviewCertificatesView(WorkBasketReviewView):
    """UI endpoint for reviewing certificate changes in a workbasket."""

    model = Certificate

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review certificates"
        context["selected_tab"] = "certificates"
        context["tab_template"] = "includes/certificates/list.jinja"
        return context


class WorkbasketReviewGoodsView(
    PermissionRequiredMixin,
    TemplateView,
):
    """UI endpoint for reviewing goods changes in a workbasket."""

    template_name = "workbaskets/review-goods.jinja"
    permission_required = "workbaskets.view_workbasket"

    @property
    def workbasket(self):
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review commodities"
        context["selected_tab"] = "commodities"
        context["user_workbasket"] = WorkBasket.current(self.request)
        context["workbasket"] = self.workbasket
        context["report_lines"] = []
        context["import_batch_pk"] = None

        # Get actual values from the ImportBatch instance if one is associated
        # with the workbasket.
        try:
            import_batch = self.workbasket.importbatch
        except ObjectDoesNotExist:
            import_batch = None

        taric_file = None
        if import_batch and import_batch.taric_file and import_batch.taric_file.name:
            taric_file = import_batch.taric_file.storage.exists(
                import_batch.taric_file.name,
            )

        if taric_file:
            reporter = GoodsReporter(import_batch.taric_file)
            goods_report = reporter.create_report()
            today = date.today()

            context["report_lines"] = [
                {
                    "update_type": line.update_type.title() if line.update_type else "",
                    "record_name": line.record_name.title() if line.record_name else "",
                    "item_id": line.goods_nomenclature_item_id,
                    "item_id_search_url": (
                        reverse("commodity-ui-list")
                        + "?"
                        + urlencode({"item_id": line.goods_nomenclature_item_id})
                        if line.goods_nomenclature_item_id
                        else ""
                    ),
                    "measures_search_url": (
                        reverse("measure-ui-list")
                        + "?"
                        + urlencode(
                            {
                                "goods_nomenclature__item_id": line.goods_nomenclature_item_id,
                                "end_date_modifier": "after",
                                "end_date_0": today.day,
                                "end_date_1": today.month,
                                "end_date_2": today.year,
                            },
                        )
                        if line.goods_nomenclature_item_id
                        else ""
                    ),
                    "suffix": line.suffix,
                    "start_date": format_date_string(
                        line.validity_start_date,
                        short_format=True,
                    ),
                    "end_date": format_date_string(
                        line.validity_end_date,
                        short_format=True,
                    ),
                    "comments": line.comments,
                }
                for line in goods_report.report_lines
            ]
            context["import_batch_pk"] = import_batch.pk

            # notifications only relevant to a goods import
            if context["workbasket"] == context["user_workbasket"]:
                context["unsent_notification"] = (
                    import_batch.goods_import
                    and not Notification.objects.filter(
                        notified_object_pk=import_batch.pk,
                        notification_type=NotificationTypeChoices.GOODS_REPORT,
                    ).exists()
                )

        return context


class WorkBasketReviewFootnotesView(WorkBasketReviewView):
    """UI endpoint for reviewing footnote changes in a workbasket."""

    model = Footnote

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review footnotes"
        context["selected_tab"] = "footnotes"
        context["tab_template"] = "includes/footnotes/list.jinja"
        return context


class WorkBasketReviewGeoAreasView(WorkBasketReviewView):
    """UI endpoint for reviewing geographical area changes in a workbasket."""

    model = GeographicalArea
    template_name = "workbaskets/review-geo-areas.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review geographical areas"
        context["selected_tab"] = "geographical-areas"
        context["selected_nested_tab"] = "geographical-areas"
        context["tab_template"] = "includes/geo_areas/list.jinja"
        return context


class WorkBasketReviewGeoMembershipsView(WorkBasketReviewView):
    """UI endpoint for reviewing geographical membership changes in a
    workbasket."""

    model = GeographicalMembership
    template_name = "workbaskets/review-geo-areas.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review geographical area group memberships"
        context["selected_tab"] = "geographical-areas"
        context["selected_nested_tab"] = "geographical-memberships"
        context["tab_template"] = "includes/workbaskets/review-geo-memberships.jinja"
        return context


class WorkBasketReviewMeasuresView(WorkBasketReviewView):
    """UI endpoint for reviewing measures in a workbasket."""

    model = Measure

    def get_queryset(self):
        return (
            Measure.objects.filter(
                transaction__workbasket=self.workbasket,
            )
            .select_related(
                "measure_type",
                "geographical_area",
                "goods_nomenclature",
                "order_number",
                "generating_regulation",
            )
            .order_by("sid")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review measures"
        context["selected_tab"] = "measures"
        context["tab_template"] = "includes/measures/workbasket-measures.jinja"
        return context


class WorkBasketReviewQuotasView(WorkBasketReviewView):
    """UI endpoint for reviewing quota changes in a workbasket."""

    model = QuotaOrderNumber
    template_name = "workbaskets/review-quotas.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review quota order numbers"
        context["selected_tab"] = "quotas"
        context["selected_nested_tab"] = "quotas"
        context["tab_template"] = "includes/quotas/list.jinja"
        return context


class WorkBasketReviewQuotaDefinitionsView(WorkBasketReviewView):
    """UI endpoint for reviewing quota definition period changes in a
    workbasket."""

    model = QuotaDefinition
    template_name = "workbaskets/review-quotas.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review quota definition periods"
        context["selected_tab"] = "quotas"
        context["selected_nested_tab"] = "quota-definitions"
        context["tab_template"] = "includes/workbaskets/review-quota-definitions.jinja"
        return context


class WorkBasketReviewSubQuotasView(WorkBasketReviewView):
    """UI endpoint for reviewing sub-quota association changes in a
    workbasket."""

    model = QuotaAssociation
    template_name = "workbaskets/review-quotas.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review sub-quota associations"
        context["selected_tab"] = "quotas"
        context["selected_nested_tab"] = "sub-quotas"
        context["tab_template"] = "includes/workbaskets/review-sub-quotas.jinja"
        return context


class WorkBasketReviewQuotaBlockingView(WorkBasketReviewView):
    """UI endpoint for reviewing quota blocking period changes in a
    workbasket."""

    model = QuotaBlocking
    template_name = "workbaskets/review-quotas.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review quota blocking periods"
        context["selected_tab"] = "quotas"
        context["selected_nested_tab"] = "blocking-periods"
        context["tab_template"] = (
            "includes/workbaskets/review-quota-blocking-periods.jinja"
        )
        return context


class WorkBasketReviewQuotaSuspensionView(WorkBasketReviewView):
    """UI endpoint for reviewing quota suspension period changes in a
    workbasket."""

    model = QuotaSuspension
    template_name = "workbaskets/review-quotas.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review quota suspension periods"
        context["selected_tab"] = "quotas"
        context["selected_nested_tab"] = "suspension-periods"
        context["tab_template"] = (
            "includes/workbaskets/review-quota-suspension-periods.jinja"
        )
        return context


class WorkBasketReviewRegulationsView(WorkBasketReviewView):
    """UI endpoint for reviewing regulation changes in a workbasket."""

    model = Regulation

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab_page_title"] = "Review regulations"
        context["selected_tab"] = "regulations"
        context["tab_template"] = "includes/regulations/list.jinja"
        return context


class NoActiveWorkBasket(TemplateView):
    """Redirect endpoint for users without an active workbasket and views that
    require one."""

    template_name = "workbaskets/no_active_workbasket.jinja"


class WorkBasketAssignUsersView(PermissionRequiredMixin, FormView):
    permission_required = "tasks.add_taskassignee"
    template_name = "workbaskets/assign_users.jinja"
    form_class = forms.WorkBasketAssignUsersForm

    @property
    def workbasket(self):
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Assign users to workbasket"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "request": self.request,
                "workbasket": self.workbasket,
            },
        )
        return kwargs

    @atomic
    def form_valid(self, form):
        task, _ = Task.objects.get_or_create(
            workbasket=self.workbasket,
            defaults={
                "title": self.workbasket.title,
                "description": self.workbasket.reason,
                "progress_state": ProgressState.objects.get(
                    name=ProgressState.State.TO_DO,
                ),
                "creator": self.request.user,
            },
        )
        form.assign_users(task=task)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("workbaskets:current-workbasket")


class WorkBasketUnassignUsersView(PermissionRequiredMixin, FormView):
    permission_required = "tasks.change_taskassignee"
    template_name = "workbaskets/assign_users.jinja"
    form_class = forms.WorkBasketUnassignUsersForm

    @property
    def workbasket(self):
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Unassign users from workbasket"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "request": self.request,
                "workbasket": self.workbasket,
            },
        )
        return kwargs

    @atomic
    def form_valid(self, form):
        form.unassign_users()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("workbaskets:current-workbasket")


class WorkBasketCommentListView(
    PermissionRequiredMixin,
    WithPaginationListMixin,
    ListView,
):
    permission_required = [
        "workbaskets.view_workbasket",
        "tasks.view_comment",
    ]
    template_name = "workbaskets/comments/list.jinja"
    paginate_by = 20

    @cached_property
    def workbasket(self):
        return WorkBasket.objects.get(pk=self.kwargs["pk"])

    def get_queryset(self):
        return Comment.objects.filter(task__workbasket=self.workbasket).order_by(
            "-created_at",
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["workbasket"] = self.workbasket
        return context


class WorkBasketCommentUpdateDeleteMixin:
    model = Comment
    success_url = reverse_lazy("workbaskets:current-workbasket")

    def editable(self, comment: Comment) -> bool:
        return (
            comment.author == self.request.user
            and comment.task.workbasket.status == WorkflowStatus.EDITING
        )

    def get_object(self, queryset=None):
        obj = super().get_object()
        if not self.editable(obj):
            raise PermissionDenied
        else:
            return obj


class WorkBasketCommentUpdate(
    PermissionRequiredMixin,
    WorkBasketCommentUpdateDeleteMixin,
    UpdateView,
):
    form_class = forms.WorkBasketCommentUpdateForm
    template_name = "workbaskets/comments/edit.jinja"
    permission_required = ["tasks.change_comment"]

    def get_initial(self):
        initial = super().get_initial()
        markdown = markdownify(self.object.content, heading_style="atx")
        initial["content"] = markdown
        return initial


class WorkBasketCommentDelete(
    PermissionRequiredMixin,
    WorkBasketCommentUpdateDeleteMixin,
    DeleteView,
):
    form_class = forms.WorkBasketCommentDeleteForm
    template_name = "workbaskets/comments/delete.jinja"
    permission_required = ["tasks.delete_comment"]


class RuleCheckQueueView(
    PermissionRequiredMixin,
    TemplateView,
):
    template_name = "workbaskets/rule_check_queue.jinja"
    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tap_tasks = TAPTasks()
        try:
            context["celery_healthy"] = True
            context["current_rule_checks"] = tap_tasks.current_tasks(
                "workbaskets.tasks.call_check_workbasket_sync",
            )
            context["status_tag_generator"] = self.status_tag_generator
        except kombu.exceptions.OperationalError as oe:
            context["celery_healthy"] = False
        context["selected_tab"] = "rule-check-queue"
        return context

    def status_tag_generator(self, task_status) -> dict:
        """Returns a dict with text and a CSS class for a UI-friendly label for
        a rule check task."""

        if task_status == "Active":
            return {
                "text": "Running",
                "tag_class": "tamato-badge-light-green",
            }
        elif task_status == "Queued":
            return {
                "text": "Queued",
                "tag_class": "tamato-badge-light-grey",
            }
        else:
            return {
                "text": task_status,
                "tag_class": "",
            }
